#!/bin/bash
cd /home/sol/luckyBot && \
git add . && \
git commit -m $1 && \
git push origin main
