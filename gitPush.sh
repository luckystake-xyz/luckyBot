#!/bin/bash
cd /home/sol/luckyBot && \
git add . && \
git add /home/sol/luckyBot/snapshots . && \
git commit -m $1 && \
git push origin main
