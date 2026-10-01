# ML-KEM C demo against liboqs. Builds only if the liboqs header and library are present.
# Override the install prefix with: make OQS_PREFIX=/path/to/liboqs
OQS_PREFIX ?= $(HOME)/_oqs
BUILD ?= build
CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -Werror -std=c11
HEADER := $(OQS_PREFIX)/include/oqs/oqs.h
LIBRARY := $(firstword $(wildcard $(OQS_PREFIX)/lib/liboqs.so $(OQS_PREFIX)/lib64/liboqs.so $(OQS_PREFIX)/lib/liboqs.a))
LIBDIR := $(dir $(LIBRARY))

.PHONY: all run clean

ifeq ($(and $(wildcard $(HEADER)),$(LIBRARY)),)
all run:
	@echo "SKIP: liboqs not found under $(OQS_PREFIX) (need include/oqs/oqs.h and lib/liboqs.so). See docs/DECISIONS.md D1."
else
all: $(BUILD)/ml_kem_demo

$(BUILD)/ml_kem_demo: ml_kem_demo.c
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I$(OQS_PREFIX)/include $< -o $@ -L$(LIBDIR) -Wl,-rpath,$(LIBDIR) -loqs

run: $(BUILD)/ml_kem_demo
	$(abspath $(BUILD))/ml_kem_demo
endif

clean:
	rm -rf $(BUILD)
