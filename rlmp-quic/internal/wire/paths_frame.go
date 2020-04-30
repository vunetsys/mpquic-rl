package wire

import (
	"bytes"
	"errors"
	"net"
	"strconv"
	"time"

	"github.com/lucas-clemente/quic-go/internal/protocol"
	"github.com/lucas-clemente/quic-go/internal/utils"
)

var (
	ErrTooManyPaths     = errors.New("PathsFrame: more paths than the maximum enabled")
	ErrTooManyIPs       = errors.New("PathsFrame: more IPs than paths")
	ErrPathsNumber      = errors.New("PathsFrame: number of paths advertised and # of paths do not match")
	ErrIPsNumber        = errors.New("PathsFrame: number of IPs and number of paths do not match")
	ErrMissingRTT       = errors.New("PathsFrame: number of paths IDs and number of remote RTTs do not match")
	ErrMissingAddrsIP   = errors.New("PathsFrame: number of paths IDs and number of remote addresses IP do not match")
	ErrMissingAddrsPort = errors.New("PathsFrame: number of paths IDs and number of remote addresses Port do not match")
)

// A PathsFrame in QUIC
type PathsFrame struct {
	MaxNumPaths uint8
	NumPaths    uint8
	NumIPs      uint8

	PathIDs         []protocol.PathID
	RemoteRTTs      []time.Duration
	RemoteAddrsIP   []string //only IPV4
	RemoteAddrsPort []string
}

func (f *PathsFrame) Write(b *bytes.Buffer, version protocol.VersionNumber) error {
	typeByte := uint8(0x12)
	b.WriteByte(typeByte)
	b.WriteByte(f.MaxNumPaths)
	b.WriteByte(f.NumPaths)
	b.WriteByte(f.NumIPs)

	if int(f.NumPaths) != len(f.PathIDs) {
		return ErrPathsNumber
	}
	if int(f.NumPaths) != int(f.NumIPs) && f.NumIPs != 0 {
		return ErrIPsNumber
	}

	if len(f.PathIDs) != len(f.RemoteRTTs) {
		return ErrMissingRTT
	}
	if len(f.PathIDs) != len(f.RemoteAddrsIP) && len(f.RemoteAddrsIP) != 0 {
		return ErrMissingAddrsIP
	}
	if len(f.PathIDs) != len(f.RemoteAddrsPort) && len(f.RemoteAddrsPort) != 0 {
		return ErrMissingAddrsPort
	}

	for i := 0; i < len(f.PathIDs); i++ {
		b.WriteByte(uint8(f.PathIDs[i]))
		utils.GetByteOrder(version).WriteUfloat16(b, uint64(f.RemoteRTTs[i]/time.Microsecond))

		//SHI: test
		if f.NumIPs > 0 {
			// if utils.Debug() {
			// 	utils.Debugf("f.RemoteAddrsIP[%d]: %s", i, f.RemoteAddrsIP[i])
			// }
			IPAddr := net.ParseIP(f.RemoteAddrsIP[i])
			ip := IPAddr.To4()
			if ip == nil {
				return errInconsistentAddrIPVersion
			}
			for i := 0; i < 4; i++ {
				b.WriteByte(ip[i])
			}

			// if utils.Debug() {
			// 	utils.Debugf("f.RemoteAddrsPort[%d]: %s", i, f.RemoteAddrsPort[i])
			// }
			portInt, err := strconv.ParseUint(f.RemoteAddrsPort[i], 10, 16)
			if err != nil {
				return err
			}
			utils.GetByteOrder(version).WriteUint16(b, uint16(portInt))

		}

	}

	return nil
}

//ParsePathsFrame SHI:add unpack of RemoteAddrsIP and RemoteAddrsPort
func ParsePathsFrame(r *bytes.Reader, version protocol.VersionNumber) (*PathsFrame, error) {
	frame := &PathsFrame{}

	// read the TypeByte
	_, err := r.ReadByte()
	if err != nil {
		return nil, err
	}

	maxNum, err := r.ReadByte()
	if err != nil {
		return nil, err
	}
	frame.MaxNumPaths = maxNum

	num, err := r.ReadByte()
	if err != nil {
		return nil, err
	}
	frame.NumPaths = num
	if frame.NumPaths > frame.MaxNumPaths {
		return nil, ErrTooManyPaths
	}

	numip, err := r.ReadByte()
	if err != nil {
		return nil, err
	}
	frame.NumIPs = numip
	if frame.NumIPs > frame.NumPaths {
		return nil, ErrTooManyIPs
	}

	for i := 0; i < int(frame.NumPaths); i++ {
		pathID, err := r.ReadByte()
		if err != nil {
			return nil, err
		}
		frame.PathIDs = append(frame.PathIDs, protocol.PathID(pathID))

		remoteRTT, err := utils.GetByteOrder(version).ReadUfloat16(r)
		if err != nil {
			return nil, err
		}
		frame.RemoteRTTs = append(frame.RemoteRTTs, time.Duration(remoteRTT)*time.Microsecond)

		if frame.NumIPs > 0 {
			//SHI: test
			a, err := r.ReadByte()
			if err != nil {
				return nil, err
			}
			b, err := r.ReadByte()
			if err != nil {
				return nil, err
			}
			c, err := r.ReadByte()
			if err != nil {
				return nil, err
			}
			d, err := r.ReadByte()
			if err != nil {
				return nil, err
			}
			IP := net.IPv4(a, b, c, d)

			frame.RemoteAddrsIP = append(frame.RemoteAddrsIP, IP.String())

			port, err := utils.GetByteOrder(version).ReadUint16(r)
			if err != nil {
				return nil, err
			}

			portStr := strconv.FormatUint(uint64(port), 10)
			frame.RemoteAddrsPort = append(frame.RemoteAddrsPort, portStr)
		}
	}

	return frame, nil
}

func (f *PathsFrame) MinLength(version protocol.VersionNumber) (protocol.ByteCount, error) {
	length := 1 + 1 + 1 + (3 * f.NumPaths)
	return protocol.ByteCount(length), nil
}
