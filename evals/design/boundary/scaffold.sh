#!/bin/bash
# A small Go service with a store of accounts, whose Account keeps the plan as a plain string.
set -euo pipefail
git init -q -b main
mkdir -p store cmd/server
cat > go.mod <<'R'
module example.com/accounts

go 1.23
R
cat > README.md <<'R'
# accounts

The service that keeps customer accounts.

    go test ./...
R
cat > store/store.go <<'R'
// Package store keeps accounts in the database.
package store

import "context"

// Account is a customer's account as it is stored.
type Account struct {
	Email string
	Plan  string
	Seats int
}

// Accounts stores accounts.
type Accounts interface {
	Create(ctx context.Context, a Account) error
}
R
cat > cmd/server/main.go <<'R'
package main

import (
	"log"
	"net/http"
)

func main() {
	mux := http.NewServeMux()
	log.Fatal(http.ListenAndServe(":8080", mux))
}
R
git add -A
git -c user.name=dev -c user.email=dev@example.com commit -q -m "Start the accounts service"
