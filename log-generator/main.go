// log-generator sends log lines to a target (file, TCP, or UDP) at max speed.
//
//	log-generator -mode file -target /tmp/bench-input.log -count 1000000
//	log-generator -mode tcp  -target localhost:9000 -count 1000000
//	log-generator -mode udp  -target localhost:9000 -count 1000000
package main

import (
	"flag"
	"fmt"
	"net"
	"os"
	"time"
)

func main() {
	mode := flag.String("mode", "file", "Output mode: file, tcp, udp")
	target := flag.String("target", "/tmp/bench-input.log", "Target path or host:port")
	count := flag.Int("count", 1000000, "Number of log lines")
	flag.Parse()

	start := time.Now()
	switch *mode {
	case "file":
		genFile(*target, *count)
	case "tcp":
		genTCP(*target, *count)
	case "udp":
		genUDP(*target, *count)
	default:
		fmt.Fprintf(os.Stderr, "unknown mode: %s\n", *mode)
		os.Exit(1)
	}
	elapsed := time.Since(start)
	fmt.Fprintf(os.Stderr, "Generated %d lines in %v (%.0f/sec)\n", *count, elapsed.Round(time.Millisecond), float64(*count)/elapsed.Seconds())
}

func line(i int) string {
	return fmt.Sprintf("2025-03-07T11:06:39.%06dZ INFO  [application] app/server.go:142 method=GET path=/api/v1/health status=200 duration_ms=3.42 request_id=req-%08x user_id=usr-%04d ip=10.0.%d.%d\n",
		i%1000000, i, i%10000, (i/256)%256, i%256)
}

func genFile(path string, count int) {
	f, err := os.Create(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "create: %v\n", err)
		os.Exit(1)
	}
	defer f.Close()
	for i := 0; i < count; i++ {
		f.WriteString(line(i))
	}
}

func genTCP(addr string, count int) {
	conn, err := net.DialTimeout("tcp", addr, 10*time.Second)
	if err != nil {
		fmt.Fprintf(os.Stderr, "connect: %v\n", err)
		os.Exit(1)
	}
	defer conn.Close()
	for i := 0; i < count; i++ {
		conn.Write([]byte(line(i)))
	}
}

func genUDP(addr string, count int) {
	raddr, _ := net.ResolveUDPAddr("udp", addr)
	conn, err := net.DialUDP("udp", nil, raddr)
	if err != nil {
		fmt.Fprintf(os.Stderr, "connect: %v\n", err)
		os.Exit(1)
	}
	defer conn.Close()
	for i := 0; i < count; i++ {
		conn.Write([]byte(line(i)))
	}
}
