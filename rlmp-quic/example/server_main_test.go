package main

import (
	"os"
	"testing"
)

func TestMainProgram(t *testing.T) {
	os.Args = []string{"./main -www .",
		" -certpath  ~/go/src/github.com/lucas-clemente/quic-go/example/",
		" -bind 0.0.0.0:6121"}
	main()
}
