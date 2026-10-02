#!/bin/bash
# Disk I/O benchmark inside the benchmark container (fio, 30 s each).
mkdir -p ~/fio-test
docker run --rm -v ~/fio-test:/fio-test vm-container-benchmark \
  fio --name=seq-write --filename=/fio-test/testfile --size=2G --bs=1M \
      --rw=write --direct=1 --iodepth=16 --runtime=30 --time_based

docker run --rm -v ~/fio-test:/fio-test vm-container-benchmark \
  fio --name=random-read --filename=/fio-test/testfile --size=2G --bs=4k \
      --rw=randread --direct=1 --iodepth=16 --runtime=30 --time_based
