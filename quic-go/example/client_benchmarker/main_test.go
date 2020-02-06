package main

import (
	"os"
	"testing"
)

func TestMainProgram(t *testing.T) {
	os.Args = []string{"./main  -m -v -c",
		" https://10.1.0.1:6121/random1 200 0",
		" https://10.1.0.1:6121/random2 10 5"}
	main()
}
