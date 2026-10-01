// Planted legacy crypto for pq_inventory tests (never executed).
package main

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha1"
	"crypto/tls"
)

func main() {
	key, _ := rsa.GenerateKey(rand.Reader, 2048)
	_ = sha1.Sum([]byte("x"))
	ec, _ := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	cfg := &tls.Config{MinVersion: tls.VersionTLS10}
	_, _, _ = key, ec, cfg
}
