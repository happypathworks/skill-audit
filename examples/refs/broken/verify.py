#!/usr/bin/env python3
"""Verify a packed archive. Exits 0 when intact, 1 when corrupt."""
import sys, zipfile
sys.exit(0 if zipfile.is_zipfile(sys.argv[1]) and zipfile.ZipFile(sys.argv[1]).testzip() is None else 1)
