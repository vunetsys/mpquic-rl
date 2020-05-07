package h2quic

import (
	"crypto/tls"
	"errors"
	"fmt"
	"net"
	"net/http"
	"runtime"
	"strconv"
	"sync"
	"sync/atomic"
	"time"

	quic "github.com/lucas-clemente/quic-go"
	"github.com/lucas-clemente/quic-go/internal/protocol"
	"github.com/lucas-clemente/quic-go/internal/utils"
	"github.com/lucas-clemente/quic-go/qerr"
	"golang.org/x/net/http2"
	"golang.org/x/net/http2/hpack"
)

type streamCreator interface {
	quic.Session
	GetOrOpenStream(protocol.StreamID) (quic.Stream, error)
	GetOrOpenStreamPriority(protocol.StreamID, *protocol.Priority) (quic.Stream, error)
	GetOrOpenStreamPrioritySize(protocol.StreamID, *protocol.Priority) (quic.Stream, error)
	GetOrOpenStreamPrioritySizePath(protocol.StreamID, *protocol.Priority, string) (quic.Stream, error)
	SetStreamPriority(protocol.StreamID, *protocol.Priority) error
}

type remoteCloser interface {
	CloseRemote(protocol.ByteCount)
}

// allows mocking of quic.Listen and quic.ListenAddr
var (
	quicListen     = quic.Listen
	quicListenAddr = quic.ListenAddr
)

// Server is a HTTP2 server listening for QUIC connections.
type Server struct {
	*http.Server

	// By providing a quic.Config, it is possible to set parameters of the QUIC connection.
	// If nil, it uses reasonable default values.
	QuicConfig *quic.Config

	// Private flag for demo, do not use
	CloseAfterFirstRequest bool

	port uint32 // used atomically

	listenerMutex sync.Mutex
	listener      quic.Listener

	supportedVersionsAsString string
}

// ListenAndServe listens on the UDP address s.Addr and calls s.Handler to handle HTTP/2 requests on incoming connections.
func (s *Server) ListenAndServe() error {
	if s.Server == nil {
		return errors.New("use of h2quic.Server without http.Server")
	}
	return s.serveImpl(s.TLSConfig, nil)
}

// ListenAndServeTLS listens on the UDP address s.Addr and calls s.Handler to handle HTTP/2 requests on incoming connections.
func (s *Server) ListenAndServeTLS(certFile, keyFile string) error {
	var err error
	certs := make([]tls.Certificate, 1)
	certs[0], err = tls.LoadX509KeyPair(certFile, keyFile)
	if err != nil {
		return err
	}
	// We currently only use the cert-related stuff from tls.Config,
	// so we don't need to make a full copy.
	config := &tls.Config{
		Certificates: certs,
	}
	return s.serveImpl(config, nil)
}

// Serve an existing UDP connection.
func (s *Server) Serve(conn net.PacketConn) error {
	return s.serveImpl(s.TLSConfig, conn)
}

func (s *Server) serveImpl(tlsConfig *tls.Config, conn net.PacketConn) error {

	if s.Server == nil {
		return errors.New("use of h2quic.Server without http.Server")
	}
	s.listenerMutex.Lock()
	if s.listener != nil {
		s.listenerMutex.Unlock()
		return errors.New("ListenAndServe may only be called once")
	}

	var ln quic.Listener
	var err error
	if conn == nil {
		ln, err = quicListenAddr(s.Addr, tlsConfig, s.QuicConfig)
	} else {
		ln, err = quicListen(conn, tlsConfig, s.QuicConfig)
	}
	if err != nil {
		s.listenerMutex.Unlock()
		return err
	}
	s.listener = ln
	s.listenerMutex.Unlock()

	for {
		sess, err := ln.Accept()
		if err != nil {
			return err
		}
		go s.handleHeaderStream(sess.(streamCreator))
	}
}

// SHI: set priority after the initiation of stream, usually not used in FStream
func (s *Server) handlePriorityFrame(session streamCreator, f *http2.PriorityFrame) error {
	dataStream, err := session.GetOrOpenStream(protocol.StreamID(f.StreamID))
	if err != nil {
		return err
	}
	// this can happen if the client immediately closes the data stream after sending the request and the runtime processes the reset before the request
	if dataStream == nil {
		return nil
	}

	session.SetStreamPriority(dataStream.StreamID(), &protocol.Priority{Dependency: protocol.StreamID(f.StreamDep), Weight: f.Weight})

	return nil
}

func (s *Server) handleHeaderStream(session streamCreator) {

	stream, err := session.AcceptStream()
	if err != nil {
		session.Close(qerr.Error(qerr.InvalidHeadersStreamData, err.Error()))
		return
	}
	if stream.StreamID() != 3 {
		session.Close(qerr.Error(qerr.InternalError, "h2quic server BUG: header stream does not have stream ID 3"))
		return
	}

	hpackDecoder := hpack.NewDecoder(4096, nil)
	h2framer := http2.NewFramer(nil, stream)

	go func() {
		var headerStreamMutex sync.Mutex // Protects concurrent calls to Write()
		for {
			if err := s.handleRequest(session, stream, &headerStreamMutex, hpackDecoder, h2framer); err != nil {
				// QuicErrors must originate from stream.Read() returning an error.
				// In this case, the session has already logged the error, so we don't
				// need to log it again.
				if _, ok := err.(*qerr.QuicError); !ok {
					utils.Errorf("error handling h2 request: %s", err.Error())
				}
				session.Close(err)
				return
			}
		}
	}()
}

func (s *Server) handleRequest(session streamCreator, headerStream quic.Stream, headerStreamMutex *sync.Mutex, hpackDecoder *hpack.Decoder, h2framer *http2.Framer) error {

	h2frame, err := h2framer.ReadFrame()
	if err != nil {
		return qerr.Error(qerr.HeadersStreamDataDecompressFailure, "cannot read frame")
	}
	var h2headersFrame *http2.HeadersFrame
	switch f := h2frame.(type) {
	case *http2.PriorityFrame:
		return s.handlePriorityFrame(session, f)
	case *http2.HeadersFrame:
		h2headersFrame = f
	default:
		return qerr.Error(qerr.InvalidHeadersStreamData, "expected a header frame")
	}
	// h2headersFrame, ok := h2frame.(*http2.HeadersFrame)
	// if !ok {
	// 	return qerr.Error(qerr.InvalidHeadersStreamData, "expected a header frame")
	// }
	if !h2headersFrame.HeadersEnded() {
		return errors.New("http2 header continuation not implemented")
	}
	headers, err := hpackDecoder.DecodeFull(h2headersFrame.HeaderBlockFragment())
	if err != nil {
		utils.Errorf("invalid http2 headers encoding: %s", err.Error())
		return err
	}

	req, err := requestFromHeaders(headers)
	if err != nil {
		return err
	}

	req.RemoteAddr = session.RemoteAddr().String()

	utils.Infof("%s %s%s, on data stream %d, with weight %d, dependency %d", req.Method, req.Host, req.RequestURI, h2headersFrame.StreamID, h2headersFrame.Priority.Weight, h2headersFrame.Priority.StreamDep)
	// utils.Infof("%s %s%s", req.Method, req.Host, req.RequestURI)

	// SHI: change to open stream with priority
	//dataStream, err := session.GetOrOpenStream(protocol.StreamID(h2headersFrame.StreamID))

	priorityTran := new(protocol.Priority)
	priorityTran.Weight = h2headersFrame.Priority.Weight
	priorityTran.Dependency = protocol.StreamID(h2headersFrame.Priority.StreamDep)
	priorityTran.Exclusive = h2headersFrame.Priority.Exclusive

	// Marios: record also request path
	dataStream, err := session.GetOrOpenStreamPrioritySizePath(protocol.StreamID(h2headersFrame.StreamID), priorityTran, req.RequestURI)
	// dataStream, err := session.GetOrOpenStreamPrioritySize(protocol.StreamID(h2headersFrame.StreamID), priorityTran)

	if err != nil {
		return err
	}
	// this can happen if the client immediately closes the data stream after sending the request and the runtime processes the reset before the request
	if dataStream == nil {
		return nil
	}

	var streamEnded bool
	if h2headersFrame.StreamEnded() {
		dataStream.(remoteCloser).CloseRemote(0)
		streamEnded = true
		_, _ = dataStream.Read([]byte{0}) // read the eof
	}

	req = req.WithContext(dataStream.Context())
	reqBody := newRequestBody(dataStream)
	req.Body = reqBody

	responseWriter := newResponseWriter(headerStream, headerStreamMutex, dataStream, protocol.StreamID(h2headersFrame.StreamID))

	go func() {
		handler := s.Handler
		if handler == nil {
			handler = http.DefaultServeMux
		}
		panicked := false
		func() {
			defer func() {
				if p := recover(); p != nil {
					// Copied from net/http/server.go
					const size = 64 << 10
					buf := make([]byte, size)
					buf = buf[:runtime.Stack(buf, false)]
					utils.Errorf("http: panic serving: %v\n%s", p, buf)
					panicked = true
				}
			}()
			// ServeHTTP should write reply headers and data to the ResponseWriter and then return.
			handler.ServeHTTP(responseWriter, req)
			// this handler is FileServer
			utils.Infof("Stream %d, Weight %d, Content-Length: %s\n", responseWriter.dataStream.StreamID(), responseWriter.dataStream.Priority().Weight, responseWriter.Header().Get("Content-Length"))
			if utils.Debug() {
				// this print out after the transmission is almost finished
				utils.Debugf("Stream %d, Content-Range: %s\n", responseWriter.dataStream.StreamID(), responseWriter.Header().Get("Content-Range"))
				utils.Debugf("Stream %d, Content-Length: %s\n", responseWriter.dataStream.StreamID(), responseWriter.Header().Get("Content-Length"))

			}

		}()
		if panicked {
			responseWriter.WriteHeader(500)
		} else {
			responseWriter.WriteHeader(200)
		}
		if responseWriter.dataStream != nil {
			if !streamEnded && !reqBody.requestRead {
				responseWriter.dataStream.Reset(nil)
			}
			responseWriter.dataStream.Close()
		}
		if s.CloseAfterFirstRequest {
			time.Sleep(100 * time.Millisecond)
			session.Close(nil)
		}
	}()

	return nil
}

// Close the server immediately, aborting requests and sending CONNECTION_CLOSE frames to connected clients.
// Close in combination with ListenAndServe() (instead of Serve()) may race if it is called before a UDP socket is established.
func (s *Server) Close() error {
	s.listenerMutex.Lock()
	defer s.listenerMutex.Unlock()
	if s.listener != nil {
		err := s.listener.Close()
		s.listener = nil
		return err
	}
	return nil
}

// CloseGracefully shuts down the server gracefully. The server sends a GOAWAY frame first, then waits for either timeout to trigger, or for all running requests to complete.
// CloseGracefully in combination with ListenAndServe() (instead of Serve()) may race if it is called before a UDP socket is established.
func (s *Server) CloseGracefully(timeout time.Duration) error {
	// TODO: implement
	return nil
}

// SetQuicHeaders can be used to set the proper headers that announce that this server supports QUIC.
// The values that are set depend on the port information from s.Server.Addr, and currently look like this (if Addr has port 443):
//  Alt-Svc: quic=":443"; ma=2592000; v="33,32,31,30"
func (s *Server) SetQuicHeaders(hdr http.Header) error {
	port := atomic.LoadUint32(&s.port)

	if port == 0 {
		// Extract port from s.Server.Addr
		_, portStr, err := net.SplitHostPort(s.Server.Addr)
		if err != nil {
			return err
		}
		portInt, err := net.LookupPort("tcp", portStr)
		if err != nil {
			return err
		}
		port = uint32(portInt)
		atomic.StoreUint32(&s.port, port)
	}

	if s.supportedVersionsAsString == "" {
		for i, v := range protocol.SupportedVersions {
			s.supportedVersionsAsString += strconv.Itoa(int(v))
			if i != len(protocol.SupportedVersions)-1 {
				s.supportedVersionsAsString += ","
			}
		}
	}

	hdr.Add("Alt-Svc", fmt.Sprintf(`quic=":%d"; ma=2592000; v="%s"`, port, s.supportedVersionsAsString))

	return nil
}

// ListenAndServeQUIC listens on the UDP network address addr and calls the
// handler for HTTP/2 requests on incoming connections. http.DefaultServeMux is
// used when handler is nil.
func ListenAndServeQUIC(addr, certFile, keyFile string, handler http.Handler, quicConfig *quic.Config) error {
	server := &Server{
		Server: &http.Server{
			Addr:    addr,
			Handler: handler,
		},
		QuicConfig: quicConfig,
	}
	return server.ListenAndServeTLS(certFile, keyFile)
}

// ListenAndServe listens on the given network address for both, TLS and QUIC
// connetions in parallel. It returns if one of the two returns an error.
// http.DefaultServeMux is used when handler is nil.
// The correct Alt-Svc headers for QUIC are set.
func ListenAndServe(addr, certFile, keyFile string, handler http.Handler, quicConfig *quic.Config) error {
	// Load certs
	var err error
	certs := make([]tls.Certificate, 1)
	certs[0], err = tls.LoadX509KeyPair(certFile, keyFile)
	if err != nil {
		return err
	}
	// We currently only use the cert-related stuff from tls.Config,
	// so we don't need to make a full copy.
	config := &tls.Config{
		Certificates: certs,
	}

	// Open the listeners
	udpAddr, err := net.ResolveUDPAddr("udp", addr)
	if err != nil {
		return err
	}
	udpConn, err := net.ListenUDP("udp", udpAddr)
	if err != nil {
		return err
	}
	defer udpConn.Close()

	tcpAddr, err := net.ResolveTCPAddr("tcp", addr)
	if err != nil {
		return err
	}
	tcpConn, err := net.ListenTCP("tcp", tcpAddr)
	if err != nil {
		return err
	}
	defer tcpConn.Close()

	tlsConn := tls.NewListener(tcpConn, config)
	defer tlsConn.Close()

	// Start the servers
	httpServer := &http.Server{
		Addr:      addr,
		TLSConfig: config,
	}

	quicServer := &Server{
		Server:     httpServer,
		QuicConfig: quicConfig,
	}

	if handler == nil {
		handler = http.DefaultServeMux
	}
	httpServer.Handler = http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		quicServer.SetQuicHeaders(w.Header())
		handler.ServeHTTP(w, r)
	})

	hErr := make(chan error)
	qErr := make(chan error)
	go func() {
		hErr <- httpServer.Serve(tlsConn)
	}()
	go func() {
		qErr <- quicServer.Serve(udpConn)
	}()

	select {
	case err := <-hErr:
		quicServer.Close()
		return err
	case err := <-qErr:
		// Cannot close the HTTP server or wait for requests to complete properly :/
		return err
	}
}
