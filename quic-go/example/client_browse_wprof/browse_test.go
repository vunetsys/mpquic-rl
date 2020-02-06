package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestMainProgram(t *testing.T) {
	absPath, _ := filepath.Abs("/Users/shixiang/Desktop/request_website_code/epload/emulator/tests/test.json")
	os.Args = []string{"./web_browse  -m -v -c ",
		absPath}
	main()
}
