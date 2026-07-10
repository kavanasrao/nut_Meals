#!/usr/bin/env bash
# Creates the secondary test database alongside the default dev DB when the
# postgres container initializes for the first time.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE cart_checkout_ext_test;
EOSQL
