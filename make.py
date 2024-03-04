#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# build libevent for iOS and macOS

import os
import sys
import subprocess
import json

def shell(cmd):
    return subprocess.check_output(cmd, shell=True).decode('utf-8').strip()

def run(cmd):
    print(cmd)
    subprocess.run(cmd, shell=True, check=True)

def mkdirp(path):
    if not os.path.exists(path):
        os.makedirs(path)

def cd(path):
    os.chdir(path)

def export(k, v):
    os.environ[k] = v

event_version = "2.1.12-stable"

platforms = {
    "iphonesimulator": "arm64",
    "iphoneos": "arm64",
    "macosx": "x86_64,arm64",
}

need_libs = "libevent.a libevent_core.a libevent_extra.a libevent_pthreads.a"

sdk_info = {}
xcode_sdks=json.loads(shell('xcodebuild -showsdks -json'))
for sdk in xcode_sdks:
    if sdk['platform'] in [x.lower() for x in platforms.keys()]:
        sdk_info[sdk['platform']] = sdk

for platform, sdk in sdk_info.items():
    print('Found sdk', platform, sdk['sdkPath'])

#sdk_version = user_sdk_ver

DEVELOPER=shell('xcode-select -print-path')
REPOROOT=shell('pwd')

# Where we'll end up storing things in the end
OUTPUTDIR=f'{REPOROOT}/dependencies'
BUILDDIR=f"{REPOROOT}/build"
SRCDIR=f"{BUILDDIR}/src"
interdir=f"{BUILDDIR}/built"

mkdirp(f'{OUTPUTDIR}/include')
mkdirp(f'{SRCDIR}')
mkdirp(f'{interdir}')

cd(SRCDIR)

if not os.path.exists(f"{SRCDIR}/libevent-{event_version}.tar.gz"):
    print(f"Downloading libevent-{event_version}.tar.gz")
    shell(f'curl -LO https://github.com/libevent/libevent/releases/download/release-{event_version}/libevent-{event_version}.tar.gz')

shell(f'tar -xzf libevent-{event_version}.tar.gz -C {SRCDIR}')
cd(f"{SRCDIR}/libevent-{event_version}")

for platform, archs in platforms.items():
    for arch in archs.split(','):
        print(f"Building libevent for {platform} {arch}")
        gcc = shell('which gcc')

        if arch == "arm64":
            EXTRA_CONFIG="--host=arm-apple-darwin"
        elif arch == "x86_64":
            EXTRA_CONFIG="--host=x86_64-apple-darwin"

        install_dir = f"{interdir}/{platform}-{arch}.sdk"
        sdk_dir = sdk_info[platform]['sdkPath']

        mkdirp(f'{install_dir}')

        #export("CC", f"{gcc} -arch {arch} -miphoneos-version-min={mini_os_version}")
        export("CC", f"{gcc} -arch {arch}")
        export("PATH", f"{DEVELOPER}/Toolchains/XcodeDefault.xctoolchain/usr/bin/:{DEVELOPER}/usr/bin:{os.environ['PATH']}")

        run(f'./configure --disable-shared --enable-static --disable-debug-mode --disable-openssl --disable-libevent-regress --disable-samples \
            {EXTRA_CONFIG} --disable-clock-gettime \
            --prefix="{install_dir}" \
            LDFLAGS="$LDFLAGS -L{OUTPUTDIR}/lib" \
            CFLAGS="$CFLAGS -Os -I{OUTPUTDIR}/include -isysroot {sdk_dir}" \
            CPPFLAGS="$CPPFLAGS -I{OUTPUTDIR}/include -isysroot {sdk_dir}"')

        run(f'make -j8')
        run(f'make install')
        run(f'make clean')


print("Copying headers and libraries")
for platform, archs in platforms.items():
    for lib in need_libs.split():
        mutiple_arch_libs = []
        for arch in archs.split(','):
            install_dir = f"{interdir}/{platform}-{arch}.sdk"
            mutiple_arch_libs.append(f"{install_dir}/lib/{lib}")
            run(f"cp -a {install_dir}/include/* {OUTPUTDIR}/include")

        mkdirp(f"{OUTPUTDIR}/lib/{platform}")
        run(f"lipo -create {' '.join(mutiple_arch_libs)} -output {OUTPUTDIR}/lib/{platform}/{lib}")

print("Done.")
