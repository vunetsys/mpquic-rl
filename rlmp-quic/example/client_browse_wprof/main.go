package main

import (
	"crypto/tls"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/buger/jsonparser"
	"github.com/headzoo/surf"
	"github.com/headzoo/surf/browser"
	quic "github.com/lucas-clemente/quic-go"
	"github.com/lucas-clemente/quic-go/h2quic"
	"github.com/lucas-clemente/quic-go/internal/utils"
	"golang.org/x/net/http2"
)

var hclient *http.Client

//ObjFinish contains the total number of objs to be download, and the current downloaded objs number
type ObjFinish struct {
	Finished    int
	Total       int
	ObjectIndex float64
	LastStamp   time.Time //time last obj finished
	Lock        sync.Mutex
}

var objFinish *ObjFinish
var start time.Time

//Download contains download information about the web object
//Type includes "evalhtml","text/html","text/css",
//"application/x-javascript","application/javascript","application/json","application/octet-stream"  //font
//"image/png","image/gif","image/jpeg"
type Download struct {
	ID           string
	Type         string //SHI: type of download files
	Started      bool
	Complete     bool
	StartTime    time.Time
	CompleteTime time.Time

	Lock sync.Mutex
}

type Comp struct {
	ID           string
	Type         string
	Time         string
	Started      bool
	Complete     bool
	StartTime    time.Time
	CompleteTime time.Time
	Lock         sync.Mutex
}

//Obj is the struct of a web object
type Obj struct {
	ID            string
	Host          string
	Path          string
	WhenCompStart string
	Comps         []*Comp
	Download      *Download
	Dependers     []*Dep
	Root          bool
	PriorityParam *http2.PriorityParam
}

//Dep is the dependency struct
type Dep struct {
	ID   string
	A1   string
	A2   string
	Time string
}

var (
	host  = "10.1.0.1:6121"
	objs  []*Obj
	count []byte
	bow   *browser.Browser
)

func parse(graphPath string) map[string]*http2.PriorityParam {
	data, err := ioutil.ReadFile(graphPath)
	if err != nil {
		panic(err)
	}
	startActivity, _, _, err := jsonparser.Get(data, "start_activity")
	// Parse objects
	jsonparser.ArrayEach(data, func(value []byte, dataType jsonparser.
		ValueType, offset int, err error) {
		obj := new(Obj)
		id, _, _, err := jsonparser.Get(value, "id")
		if err != nil {
			panic(err)
		}
		// host, _, _, err := jsonparser.Get(value, "host")
		// if err != nil {
		// 	panic(err)
		// }

		pth, _, _, err := jsonparser.Get(value, "path")
		if err != nil {
			panic(err)
		}
		WhenCompStart, _, _, err := jsonparser.Get(value, "when_comp_start")
		if err != nil {
			panic(err)
		}
		obj.ID = string(id)
		obj.Host = string(host)
		obj.Path = string(pth)
		obj.WhenCompStart = string(WhenCompStart)
		// Parse computations
		jsonparser.ArrayEach(value, func(value []byte, dataType jsonparser.ValueType, offset int, err error) {
			comp := new(Comp)
			compID, _, _, err := jsonparser.Get(value, "id")
			if err != nil {
				panic(err)
			}
			compType, _, _, err := jsonparser.Get(value, "type")
			if err != nil {
				panic(err)
			}
			compTime, _, _, err := jsonparser.Get(value, "time")
			if err != nil {
				panic(err)
			}

			comp.ID = string(compID)
			comp.Type = string(compType)
			comp.Time = string(compTime)
			//XXX: To disable sleep times
			//comp.Time = "0"
			obj.Comps = append(obj.Comps, comp)
		}, "comps")
		// Parse download
		download := new(Download)
		downloadID, _, _, err := jsonparser.Get(value, "download", "id")
		if err != nil {
			panic(err)
		}
		downloadType, _, _, err := jsonparser.Get(value, "download", "type")
		if err != nil {
			panic(err)
		}
		download.ID = string(downloadID)
		download.Type = string(downloadType)
		obj.Download = download
		if string(startActivity) == download.ID {
			obj.Root = true
		}
		objs = append(objs, obj)
	}, "objs")

	// Parse dependencies
	var deps []*Dep
	jsonparser.ArrayEach(data, func(value []byte, dataType jsonparser.
		ValueType, offset int, err error) {
		dep := new(Dep)
		id, _, _, err := jsonparser.Get(value, "id")
		if err != nil {
			panic(err)
		}
		a1, _, _, err := jsonparser.Get(value, "a1")
		if err != nil {
			panic(err)
		}
		a2, _, _, err := jsonparser.Get(value, "a2")
		if err != nil {
			panic(err)
		}
		time, _, _, err := jsonparser.Get(value, "time")
		if err != nil {
			panic(err)
		}
		dep.ID = string(id)
		dep.A1 = string(a1)
		dep.A2 = string(a2)
		dep.Time = string(time)
		deps = append(deps, dep)
	}, "deps")

	// Add dependencies and priorities to objects //priorities: partially Chrome 58
	priorityURL := make(map[string]*http2.PriorityParam)

	for _, obj := range objs {
		if strings.Contains(obj.Download.Type, "html") || strings.Contains(obj.Download.Type, "css") || strings.Contains(obj.Download.Type, "octet-stream") {
			obj.PriorityParam = &http2.PriorityParam{Weight: 255}
		} else if strings.Contains(obj.Download.Type, "javascript") || strings.Contains(obj.Download.Type, "js") {
			obj.PriorityParam = &http2.PriorityParam{Weight: 220}

		} else if strings.Contains(obj.Download.Type, "image") {
			obj.PriorityParam = &http2.PriorityParam{Weight: 147}
		} else {
			obj.PriorityParam = &http2.PriorityParam{Weight: 110}
		}
		priorityURL["https://"+host+obj.Path] = obj.PriorityParam

		for _, dep := range deps {
			if dep.A1 == obj.Download.ID {
				obj.Dependers = append(obj.Dependers, dep)
			} else {
				for _, comp := range obj.Comps {
					if dep.A1 == comp.ID {
						obj.Dependers = append(obj.Dependers, dep)
					}
				}
			}
		}
	}
	return priorityURL
}
func checkDependedActivities(id string) bool {
	for _, obj := range objs {
		for _, dep := range obj.Dependers {
			if id == dep.A2 {
				t, err := strconv.ParseFloat(dep.Time, 64)
				if err != nil {
					panic(err)
				}
				// Handle download activity,
				// SHI: still have to wait dep.Time after the dependent stream was finished
				if obj.Download.ID == dep.A1 {
					obj.Download.Lock.Lock()
					if t < 0 && !obj.Download.Complete {
						// Must wait for the entire download to complete
						obj.Download.Lock.Unlock()
						return false
					}
					if t > 0 && !obj.Download.Started {

						// Download has not started yet
						obj.Download.Lock.Unlock()
						return false
					}
					if t > 0 {
						elapsed := time.Since(obj.Download.StartTime)
						waitTime, err := time.ParseDuration(dep.Time + "ms")
						if err != nil {
							obj.Download.Lock.Unlock()
							panic(err)
						}
						if elapsed < waitTime {
							// Still cannot start
							obj.Download.Lock.Unlock()
							return false
						}
					}
					obj.Download.Lock.Unlock()
				}
				// Handle comp activity
				for _, comp := range obj.Comps {
					if comp.ID == dep.A1 {
						comp.Lock.Lock()
						if t < 0 && !comp.Complete {
							// Must wait for computation to complete
							comp.Lock.Unlock()
							return false
						}
						if t > 0 && !comp.Started {
							// Computation has not started yet

							comp.Lock.Unlock()

							return false
						}
						if t > 0 {
							elapsed := time.Since(comp.StartTime)
							waitTime, err := time.ParseDuration(dep.Time + "ms")
							if err != nil {
								comp.Lock.Unlock()
								panic(err)
							}
							if elapsed < waitTime {
								// Still cannot start
								comp.Lock.Unlock()
								return false
							}
						}
						comp.Lock.Unlock()
					}
				}
			}
		}
	}
	return true
}

func compute(obj *Obj, comp *Comp) {
	comp.Lock.Lock()
	if comp.Started {
		comp.Lock.Unlock()
		return
	}
	comp.Lock.Unlock()

	var wg sync.WaitGroup
	wg.Add(2)
	go func(comp *Comp) {
		defer wg.Done()
		for {
			// Check whether all depended activities are done
			ok := checkDependedActivities(comp.ID)
			if ok /* Wait for computation */ {
				var sleepTime time.Duration
				if comp.Time != "0" {
					st, err := time.ParseDuration(comp.Time + "ms")
					if err != nil {
						panic(err)
					}
					sleepTime = st
				}
				comp.Lock.Lock()
				comp.Started = true
				comp.StartTime = time.Now()
				comp.Lock.Unlock()
				start := time.Now()
				for {
					elapsed := time.Since(start)
					if elapsed >= sleepTime {
						break
					}
				}
				comp.Lock.Lock()
				comp.Complete = true

				comp.CompleteTime = time.Now()
				comp.Lock.Unlock()
				break
			}
		}
	}(comp)
	go func(comp *Comp) {
		defer wg.Done()
		processDependers(obj, comp.ID)
	}(comp)
	wg.Wait()
}
func processDependers(obj *Obj, id string) {
	var wg sync.WaitGroup
	for _, dep := range obj.Dependers {
		if id == dep.A1 {
			for _, o := range objs {
				if o.Download.ID == dep.A2 {
					wg.Add(1)
					go func(o *Obj) {
						defer wg.Done()
						for {
							ok := checkDependedActivities(o.Download.ID)
							if ok {
								get(o)
								break
							}
						}
					}(o)
				}
				for _, comp := range o.Comps {
					if comp.ID == dep.A2 {
						wg.Add(1)
						go func(o *Obj) {
							defer wg.Done()
							ok := checkDependedActivities(o.Download.ID)
							if ok {
								compute(o, comp)
							}
						}(o)
					}
				}
			}
		}
	}
	wg.Wait()
}
func get(obj *Obj) {
	obj.Download.Lock.Lock()
	if obj.Download.Started {
		obj.Download.Lock.Unlock()
		return
	}
	obj.Download.Lock.Unlock()
	// Emulate computation before the entire object has been downloaded
	var wg sync.WaitGroup
	mayComp := false
	if obj.WhenCompStart == "1" {
		wg.Add(1)
		go func(pth string) {

			defer wg.Done()
			//err := bow.Head(pth) //original send request
			utils.Infof("get url %s through Head\n", pth)
			_, err := hclient.Head(pth) //SHI
			if err != nil {
				panic(err)
			}
			mayComp = true
		}("https://" + host + obj.Path)
	}
	wg.Add(1)
	go func(pth string) {
		defer wg.Done()
		obj.Download.Lock.Lock()
		obj.Download.Started = true
		obj.Download.StartTime = time.Now()
		obj.Download.Lock.Unlock()

		utils.Infof(time.Now().Format(time.StampMilli), ": GET", pth)

		//err := bow.Open(pth) //original send request
		_, err := hclient.Get(pth) //SHI
		if err != nil {
			panic(err)
		}
		obj.Download.Lock.Lock()
		obj.Download.Complete = true
		obj.Download.CompleteTime = time.Now()
		obj.Download.Lock.Unlock()

		// SHI: compute ObjectIndex
		objFinish.Lock.Lock()
		objFinish.Finished++

		var timeGap float64
		if objFinish.Finished == 1 { // if the first downloaded obj
			timeGap = obj.Download.CompleteTime.Sub(start).Seconds()
		} else {
			timeGap = obj.Download.CompleteTime.Sub(objFinish.LastStamp).Seconds()
		}
		finishedRatio := float64(objFinish.Finished) / float64(objFinish.Total)
		incre := (1 - finishedRatio) * timeGap
		objFinish.LastStamp = obj.Download.CompleteTime
		objFinish.ObjectIndex += incre

		if utils.Debug() {
			utils.Debugf("start = %s, objFinish.LastStamp = %s, Finished = %d, Total = %d, timeGap = %f, finishedRatio = %f, ObjectIndex = %f\n",
				start.String(), objFinish.LastStamp.String(), objFinish.Finished, objFinish.Total, timeGap, finishedRatio, objFinish.ObjectIndex)
		}

		if objFinish.Finished == objFinish.Total {
			// record final result
			utils.Infof("ObjectIndex = %f\n", objFinish.ObjectIndex)
		}
		objFinish.Lock.Unlock()

	}("https://" + host + obj.Path)
	// Wait for download to complete or first data
	for {

		if obj.WhenCompStart == "1" && mayComp {
			break
		}
		obj.Download.Lock.Lock()
		if obj.Download.Complete {
			obj.Download.Lock.Unlock()
			break
		}
		obj.Download.Lock.Unlock()
	}
	// Handle computations
	if len(obj.Comps) > 0 {
		if checkDependedActivities(obj.Comps[0].ID) {
			if !obj.Comps[0].Started {
				compute(obj, obj.Comps[0])
			}
		}
	}
	processDependers(obj, obj.Download.ID)
	wg.Wait()
}

func onCompletion(start time.Time) {
	fmt.Println("Number of objects:", len(objs))
	var longest time.Time
	for _, obj := range objs {
		//SHI: render time is the finish time of the last computation of a html/css
		if obj.Download.Type == "text/html" || obj.Download.Type == "text/css" {
			for _, comp := range obj.Comps {

				if longest.Before(comp.CompleteTime) {
					longest = comp.CompleteTime
				}
			}
		}
		objCompletionTime := obj.Download.CompleteTime.Sub(obj.Download.
			StartTime)
		fmt.Println("obj", obj.ID, obj.Download.Type, "z",
			objCompletionTime)
	}
	elapsed := time.Since(start).Seconds()
	fmt.Println("Page Load Time (8):", elapsed)
	elapsed = longest.Sub(start).Seconds()
	fmt.Println("Render Time (8):", elapsed)
}
func main() {
	verbose := flag.Bool("v", false, "verbose")
	multipath := flag.Bool("m", false, "multipath")
	output := flag.String("o", "", "logging output")
	cache := flag.Bool("c", false, "cache handshake information")
	// bindAddr = flag.String("b", "0.0.0.0", "bind address")
	pathScheduler := flag.String("ps", "", "path scheduler")
	// streamScheduler = flag.String("ss", "RoundRobin", "stream scheduler")

	flag.Parse()
	graphPath := flag.Args()
	if len(graphPath) == 0 {
		fmt.Println("Specify input file")
		return
	}
	if *verbose {
		utils.SetLogLevel(utils.LogLevelDebug)
	} else {
		utils.SetLogLevel(utils.LogLevelInfo)
	}
	if *output != "" {
		logfile, err := os.Create(*output)
		if err != nil {
			panic(err)
		}
		defer logfile.Close()
		log.SetOutput(logfile)
	}

	utils.Infof("Begin parse\n")

	priorityURL := parse(graphPath[0])

	if utils.Debug() {
		utils.Debugf("Priority URL: \n")
		for k, v := range priorityURL {
			utils.Debugf("url %s, priority %d\n", k, v.Weight)
		}
		utils.Debugf("\n\n")

		for _, obj := range objs {
			utils.Debugf("host = %s, obj.Host = %s, obj.Path = %s\n", host, obj.Host, obj.Path)
			_, ok := priorityURL["https://"+host+obj.Path]
			if !ok {

				utils.Debugf("%s miss priority\n", "https://"+host+obj.Path)

			}
		}
	}

	// ======== begin browse ========
	utils.Infof("Begin browse: obj number = %d\n", len(objs))

	objFinish = &ObjFinish{}
	objFinish.Lock.Lock()
	objFinish.Total = len(objs)
	objFinish.Lock.Unlock()

	bow = surf.NewBrowser()
	quicConfig := &quic.Config{
		CreatePaths:    *multipath,
		CacheHandshake: *cache,
		// BindAddr:       *bindAddr,
		PathScheduler: *pathScheduler,

		// StreamScheduler: *streamScheduler,
	}

	roundTripper := &h2quic.RoundTripper{
		QuicConfig: quicConfig,
		//TLSClientConfig: tlsConfig,
		PriorityURL:     priorityURL,
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}

	hclient = &http.Client{
		Transport: roundTripper,
	}

	bow.SetTransport(roundTripper)
	start = time.Now()
	for _, obj := range objs {
		if obj.Root {
			get(obj)
		}
	}
	onCompletion(start)
}
