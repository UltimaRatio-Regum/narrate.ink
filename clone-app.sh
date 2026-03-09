#!/bin/bash
app_name="${1:-VoxLibris}"
cd ~
rm "$app_name".7z 2>/dev/null
7z a "$app_name".7z workspace/[^.]* -xr\!node_modules
result_7z="$?"
dest_folder="$app_name"'.'$(date +%s.%N)
if [[ "$?" -eq 0 ]]
then
    rsync -aPW --inplace --size-only "$app_name".7z root@dl-fast.ntj.services:
    ssh root@dl-fast.ntj.services rsync "$app_name".7z 192.168.55.66:
    ssh -J root@dl-fast.ntj.services root@192.168.55.66 mkdir \"$dest_folder\" \&\& cd \"$dest_folder\" \&\& 7z x ../\"$app_name\".7z \&\& ./workspace/docker-build.sh
fi
