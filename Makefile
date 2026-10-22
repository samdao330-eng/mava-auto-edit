# MAVA AUTO EDIT — make setup (máy mới), make test (sau khi sửa engine/ hoặc channels/)
.DEFAULT_GOAL := setup
.PHONY: setup test check version

setup:
	@./autoedit setup

test:
	@tests/regression.sh

check:          # make check XML="<file.xml>"
	@./autoedit check "$(XML)"

version:
	@./autoedit version
