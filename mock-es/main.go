// mock-es is a minimal Elasticsearch mock that accepts and discards bulk data.
// It responds just enough to satisfy filebeat's startup handshake and bulk indexing.
package main

import (
	"compress/gzip"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

var (
	docsIngested  atomic.Int64
	bytesReceived atomic.Int64
	batchCount    atomic.Int64
	batchDocsMin  atomic.Int64
	batchDocsMax  atomic.Int64
	startTimeNano atomic.Int64
	startOnce     sync.Once
)

func getStartTime() time.Time {
	nanos := startTimeNano.Load()
	if nanos == 0 {
		return time.Now()
	}
	return time.Unix(0, nanos)
}

func setStartTime(t time.Time) {
	startTimeNano.Store(t.UnixNano())
}

func main() {
	addr := ":9200"
	if len(os.Args) > 1 {
		addr = os.Args[1]
	}

	mux := http.NewServeMux()

	// Stats endpoint
	mux.HandleFunc("GET /_mock/stats", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		docs := docsIngested.Load()
		batches := batchCount.Load()
		bytes := bytesReceived.Load()
		elapsed := time.Since(getStartTime()).Seconds()
		var docsPerSec float64
		var avgBatchSize float64
		if elapsed > 0 {
			docsPerSec = float64(docs) / elapsed
		}
		if batches > 0 {
			avgBatchSize = float64(docs) / float64(batches)
		}
		fmt.Fprintf(w, `{"docs_ingested":%d,"bytes_received":%d,"batches":%d,"batch_docs_min":%d,"batch_docs_max":%d,"avg_batch_size":%.1f,"elapsed_sec":%.1f,"docs_per_sec":%.0f}`,
			docs, bytes, batches, batchDocsMin.Load(), batchDocsMax.Load(), avgBatchSize, elapsed, docsPerSec)
	})

	// Reset stats
	mux.HandleFunc("POST /_mock/reset", func(w http.ResponseWriter, r *http.Request) {
		docsIngested.Store(0)
		bytesReceived.Store(0)
		batchCount.Store(0)
		batchDocsMin.Store(0)
		batchDocsMax.Store(0)
		setStartTime(time.Now())
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, `{"reset":true}`)
	})

	// Catch-all: route everything through a single handler that inspects
	// the path to decide what to return. This avoids Go 1.22+ ServeMux
	// pattern conflicts between method-specific and wildcard routes.
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Elastic-Product", "Elasticsearch")
		w.Header().Set("Content-Type", "application/json")

		path := r.URL.Path

		// Bulk ingest — accept and discard
		if r.Method == "POST" && (path == "/_bulk" || len(path) > 6 && path[len(path)-6:] == "/_bulk") {
			bulkHandler(w, r)
			return
		}

		// Drain any request body
		io.Copy(io.Discard, r.Body)

		switch {
		case r.Method == "GET" && path == "/":
			// Cluster info
			fmt.Fprint(w, `{"name":"mock","cluster_name":"mock","cluster_uuid":"mock","version":{"number":"8.17.0","build_flavor":"default","build_type":"docker","lucene_version":"9.12.0","minimum_wire_compatibility_version":"7.17.0","minimum_index_compatibility_version":"7.0.0"},"tagline":"You Know, for Search"}`)
		case r.Method == "GET" && path == "/_license":
			fmt.Fprint(w, `{"license":{"uid":"mock","type":"trial","status":"active","expiry_date_in_millis":4102444800000}}`)
		case strings.HasPrefix(path, "/_index_template") && r.Method == "GET":
			fmt.Fprint(w, `{"index_templates":[]}`)
		case strings.HasPrefix(path, "/_component_template") && r.Method == "GET":
			fmt.Fprint(w, `{"component_templates":[]}`)
		case strings.HasPrefix(path, "/_ilm/policy") && r.Method == "GET":
			fmt.Fprint(w, `{}`)
		default:
			fmt.Fprint(w, `{"acknowledged":true}`)
		}
	})

	fmt.Fprintf(os.Stderr, "mock-es listening on %s\n", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		fmt.Fprintf(os.Stderr, "mock-es: %v\n", err)
		os.Exit(1)
	}
}

func bulkHandler(w http.ResponseWriter, r *http.Request) {
	startOnce.Do(func() { setStartTime(time.Now()) })

	var bodyReader io.Reader = r.Body
	if r.Header.Get("Content-Encoding") == "gzip" {
		gz, err := gzip.NewReader(r.Body)
		if err == nil {
			defer gz.Close()
			bodyReader = gz
		}
	}

	body, _ := io.ReadAll(bodyReader)
	bytesReceived.Add(int64(len(body)))

	docs := 0
	for i := 0; i < len(body); {
		if body[i] == '{' && i+8 < len(body) {
			prefix := string(body[i : i+8])
			if prefix == `{"create` || prefix == `{"index"` || prefix == `{"update` || prefix == `{"delete` {
				docs++
			}
		}
		for i < len(body) && body[i] != '\n' {
			i++
		}
		i++
	}
	if docs < 1 && len(body) > 0 {
		docs = 1
	}

	docsIngested.Add(int64(docs))
	batchCount.Add(1)

	// Track min/max batch sizes (lock-free)
	d := int64(docs)
	for {
		cur := batchDocsMin.Load()
		if cur != 0 && cur <= d {
			break
		}
		if batchDocsMin.CompareAndSwap(cur, d) {
			break
		}
	}
	for {
		cur := batchDocsMax.Load()
		if cur >= d {
			break
		}
		if batchDocsMax.CompareAndSwap(cur, d) {
			break
		}
	}

	w.Header().Set("X-Elastic-Product", "Elasticsearch")
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"took":1,"errors":false,"items":[`))
	for i := 0; i < docs; i++ {
		if i > 0 {
			w.Write([]byte(","))
		}
		w.Write([]byte(`{"create":{"_index":"mock","_id":"mock","_version":1,"result":"created","status":201}}`))
	}
	w.Write([]byte("]}"))
}
