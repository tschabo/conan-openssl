from conans import ConanFile, AutoToolsBuildEnvironment
from conans import tools
from conans import __version__ as client_version
import os

from conans.model.version import Version


class OpenSSLConan(ConanFile):
    name = "OpenSSL"
    version = "1.0.2p"
    settings = "os", "compiler", "arch", "build_type"
    url = "http://github.com/lasote/conan-openssl"
    license = "The current OpenSSL licence is an 'Apache style' license: https://www.openssl.org/source/license.html"
    description = "OpenSSL is an open source project that provides a robust, commercial-grade, and full-featured " \
                  "toolkit for the Transport Layer Security (TLS) and Secure Sockets Layer (SSL) protocols"
    # https://github.com/openssl/openssl/blob/OpenSSL_1_0_2l/INSTALL
    options = {"no_threads": [True, False],
               "no_zlib": [True, False],
               "shared": [True, False],
               "no_asm": [True, False],
               "386": [True, False],
               "no_sse2": [True, False],
               "no_bf": [True, False],
               "no_cast": [True, False],
               "no_des": [True, False],
               "no_dh": [True, False],
               "no_dsa": [True, False],
               "no_hmac": [True, False],
               "no_md2": [True, False],
               "no_md5": [True, False],
               "no_mdc2": [True, False],
               "no_rc2": [True, False],
               "no_rc4": [True, False],
               "no_rc5": [True, False],
               "no_rsa": [True, False],
               "no_sha": [True, False]}
    default_options = "=False\n".join(options.keys()) + "=False\n zlib:shared=False"
    exports_sources = "*.tar.gz"

    # When a new version is available they move the tar.gz to old/ location
    source_tgz = "https://www.openssl.org/source/openssl-%s.tar.gz" % version
    source_tgz_old = "https://www.openssl.org/source/old/1.0.2/openssl-%s.tar.gz" % version

    def build_requirements(self):
        # useful for example for conditional build_requires
        if self.settings.compiler == "Visual Studio":
            self.build_requires("strawberryperl/5.26.0@snow-crash/testing")
            if not self.options.no_asm and self.settings.arch == "x86":
                self.build_requires("nasm/2.13.01@snow-crash/testing")

    def source(self):
        tools.unzip("openssl-1.0.2p.tar.gz")
        tools.check_sha256("openssl-1.0.2p.tar.gz",
                           "50a98e07b1a89eb8f6a99477f262df71c6fa7bef77df4dc83025a2845c827d00")
        os.unlink("openssl-1.0.2p.tar.gz")

    def configure(self):
        if client_version < Version("1.0.0"):
            raise Exception("This recipe only works with Conan client >= 1.0.0")
        del self.settings.compiler.libcxx

    def requirements(self):
        if not self.options.no_zlib:
            self.requires("zlib/1.2.11@snow-crash/testing")

    @property
    def subfolder(self):
        return "openssl-%s" % self.version

    def build(self):
        """
            For Visual Studio (tried with 2010) compiling need:
             - perl: http://www.activestate.com/activeperl/downloads
             - nasm: http://www.nasm.us/
            Put perl and nasm bin folder in USER PATH (not system path, so the visual 2010 command system symbol can find it)
            Open the visual 2010 command system symbol and run conan.
            Here are good page explaining it: http://hostagebrain.blogspot.com.es/2015/04/build-openssl-on-windows.html
        """
        config_options_string = ""
        if "zlib" in self.deps_cpp_info.deps:
            zlib_info = self.deps_cpp_info["zlib"]
            include_path = zlib_info.include_paths[0]
            if self.settings.os == "Windows":
                lib_path = "%s/%s.lib" % (zlib_info.lib_paths[0], zlib_info.libs[0])
            else:
                lib_path = zlib_info.lib_paths[0]  # Just path, linux will find the right file
            config_options_string += ' --with-zlib-include="%s"' % include_path
            config_options_string += ' --with-zlib-lib="%s"' % lib_path

            tools.replace_in_file("./%s/Configure" % self.subfolder, "::-lefence::", "::")
            tools.replace_in_file("./%s/Configure" % self.subfolder, "::-lefence ", "::")
            self.output.info("=====> Options: %s" % config_options_string)
        if self.settings.os == "Android" and self.settings.compiler == "clang":
            tools.replace_in_file("./openssl-%s/Configure" % self.version, 
                                '''"android-armv7","gcc:-march=armv7-a -mandroid -I\$(ANDROID_DEV)/include -B\$(ANDROID_DEV)/lib -O3 -fomit-frame-pointer -Wall::-D_REENTRANT::-ldl:BN_LLONG RC4_CHAR RC4_CHUNK DES_INT DES_UNROLL BF_PTR:${armv4_asm}:dlfcn:linux-shared:-fPIC::.so.\$(SHLIB_MAJOR).\$(SHLIB_MINOR)",''',
                                '''"android-armv7","clang:$ENV{'CFLAGS'} -O3 -fomit-frame-pointer -Wall::-D_REENTRANT::-ldl $ENV{'LDFLAGS'}:BN_LLONG RC4_CHAR RC4_CHUNK DES_INT DES_UNROLL BF_PTR:${armv4_asm}:dlfcn:linux-shared:-fPIC::.so.\$(SHLIB_MAJOR).\$(SHLIB_MINOR)",''')

        for option_name in self.options.values.fields:
            activated = getattr(self.options, option_name)
            if activated:
                self.output.info("Activated option! %s" % option_name)
                config_options_string += " %s" % option_name.replace("_", "-")

        if self.settings.os in ["Linux", "SunOS", "FreeBSD", "Android"]:
            self.unix_build(config_options_string)
        elif self.settings.os == "Windows" and tools.os_info.is_linux:
            self.unix_build(config_options_string)
        elif self.settings.os == "Macos":
            self.osx_build(config_options_string)
        elif self.settings.os == "iOS":
            self.ios_build(config_options_string)
        elif self.settings.compiler == "Visual Studio":
            self.visual_build(config_options_string)
        elif self.settings.os == "Windows" and self.settings.compiler == "gcc":
            self.mingw_build(config_options_string)
        else:
            raise Exception("Unsupported operating system: %s" % self.settings.os)

        self.output.info("----------BUILD END-------------")

    def run_in_src(self, command, show_output=False):
        if not show_output and self.settings.os != "Windows":
            command += ' | while read line; do printf "%c" .; done'
            # pipe doesn't fail if first part fails
            command = 'bash -l -c -o pipefail "%s"' % command.replace('"', '\\"')
        with tools.chdir(self.subfolder):
            self.run(command)
        self.output.writeln(" ")

    def unix_build(self, config_options_string):
        env_build = AutoToolsBuildEnvironment(self)
        extra_flags = ' '.join(env_build.flags)
        target_prefix = ""
        if self.settings.build_type == "Debug":
            config_options_string = " no-asm" + config_options_string
            extra_flags += " -O0"
            target_prefix = "debug-"
            if self.settings.compiler in ["apple-clang", "clang", "gcc"]:
                extra_flags += " -g3 -fno-omit-frame-pointer -fno-inline-functions"

        if self.settings.os == "Linux":
            if self.settings.arch == "x86":
                target = "%slinux-generic32" % target_prefix
            elif self.settings.arch == "x86_64":
                target = "%slinux-x86_64" % target_prefix
            elif self.settings.arch == "armv8":  # Thanks @dashaomai!
                target = "%slinux-aarch64" % target_prefix
            elif str(self.settings.arch) in ("ppc64le", "ppc64", "mips64", "sparcv9"):
                target = "linux-%s" % str(self.settings.arch)
            elif "arm" in self.settings.arch:
                target = "linux-armv4"
            elif "mips" == self.settings.arch:
                target = "linux-mips32"
            else:
                raise Exception("Unsupported arch for Linux")

        elif self.settings.os == "Android":
            if "armv7" in self.settings.arch:
                target = "android-armv7"
            elif self.settings.arch == "armv8":
                target = "android-aarch64"
            elif self.settings.arch == "x86":
                target = "android-x86"
            elif self.settings.arch == "mips":
                target = "android-mips"
            else:
                raise Exception("Unsupported arch for Android")
        elif self.settings.os == "SunOS":
            if self.settings.compiler in ["apple-clang", "clang", "gcc"]:
                suffix = "-gcc"
            elif self.settings.compiler == "sun-cc":
                suffix = "-cc"
            else:
                raise Exception("Unsupported compiler on SunOS: %s" % self.settings.compiler)

            # OpenSSL has no debug profile for non sparcv9 machine
            if self.settings.arch != "sparcv9":
                target_prefix = ""

            if self.settings.arch in ["sparc", "x86"]:
                target = "%ssolaris-%s%s" % (target_prefix, self.settings.arch, suffix)
            elif self.settings.arch in ["sparcv9", "x86_64"]:
                target = "%ssolaris64-%s%s" % (target_prefix, self.settings.arch, suffix)
            else:
                raise Exception("Unsupported arch on SunOS: %s" % self.settings.arch)

        elif self.settings.os == "FreeBSD":
            target = "%sBSD-%s" % (target_prefix, self.settings.arch)
        elif self.settings.os == "Windows" and self.settings.arch == "x86_64":
            target = "mingw64"
        elif self.settings.os == "Windows" and self.settings.arch == "x86":
            target = "mingw"
        else:
            raise Exception("Unsupported operating system: %s" % self.settings.os)

        config_line = "./Configure %s -fPIC %s %s" % (config_options_string, target, extra_flags)

        self.output.warn(config_line)
        self.run_in_src(config_line)
        if not tools.cross_building(self.settings):
            self.run_in_src("make depend")
        self.output.warn("----------MAKE OPENSSL %s-------------" % self.version)
        self.run_in_src("make", show_output=True)

    def ios_build(self, config_options_string):
        def find_sysroot(sdk_name):
            return tools.XCRun(self.settings, sdk_name).sdk_path

        def find_cc(settings, sdk_name=None):
            return tools.XCRun(settings, sdk_name).cc

        command = "./Configure iphoneos-cross %s" % config_options_string

        sdk = tools.apple_sdk_name(self.settings)
        sysroot = find_sysroot(sdk)
        cc = find_cc(self.settings, sdk)

        cc += " -arch %s" % tools.to_apple_arch(self.settings.arch)
        if not str(self.settings.arch).startswith("arm"):
            cc += " -DOPENSSL_NO_ASM"

        os.environ["CROSS_SDK"] = os.path.basename(sysroot)
        os.environ["CROSS_TOP"] = os.path.dirname(os.path.dirname(sysroot))

        command = 'CC="%s" %s' % (cc, command)

        self.run_in_src(command)
        # REPLACE -install_name FOR FOLLOW THE CONAN RULES,
        # DYNLIBS IDS AND OTHER DYNLIB DEPS WITHOUT PATH, JUST THE LIBRARY NAME
        old_str = 'SHAREDFLAGS="$$SHAREDFLAGS -install_name $(INSTALLTOP)/$(LIBDIR)/$$SHLIB$'
        new_str = 'SHAREDFLAGS="$$SHAREDFLAGS -install_name $$SHLIB$'
        tools.replace_in_file("./%s/Makefile.shared" % self.subfolder, old_str, new_str)
        self.output.warn("----------MAKE OPENSSL %s-------------" % self.version)
        self.run_in_src("make")

    def osx_build(self, config_options_string):
        m32_suff = " -m32" if self.settings.arch == "x86" else ""
        if self.settings.arch == "x86_64":
            command = "./Configure darwin64-x86_64-cc %s" % config_options_string
        else:
            command = "./config %s %s" % (config_options_string, m32_suff)

        self.run_in_src(command)
        # REPLACE -install_name FOR FOLLOW THE CONAN RULES,
        # DYNLIBS IDS AND OTHER DYNLIB DEPS WITHOUT PATH, JUST THE LIBRARY NAME
        old_str = 'SHAREDFLAGS="$$SHAREDFLAGS -install_name $(INSTALLTOP)/$(LIBDIR)/$$SHLIB$'
        new_str = 'SHAREDFLAGS="$$SHAREDFLAGS -install_name $$SHLIB$'
        tools.replace_in_file("./%s/Makefile.shared" % self.subfolder, old_str, new_str)
        self.output.warn("----------MAKE OPENSSL %s-------------" % self.version)
        self.run_in_src("make")

    def visual_build_(self, config_options_string):
        self.run_in_src("perl --version")

        self.output.warn("----------CONFIGURING OPENSSL FOR WINDOWS. %s-------------" % self.version)
        debug = "debug-" if self.settings.build_type == "Debug" else ""
        arch = "32" if self.settings.arch == "x86" else "64A"
        configure_type = debug + "VC-WIN" + arch
        no_asm = "no-asm" if self.options.no_asm else ""
        
        config_command = "perl Configure %s %s --prefix=../binaries" % (configure_type, no_asm)
        whole_command = "%s %s" % (config_command, config_options_string)
        self.output.warn(whole_command)
        self.run_in_src(whole_command)

        if not self.options.no_asm and self.settings.arch == "x86":
            # The 64 bits builds do not require the do_nasm
            # http://p-nand-q.com/programming/windows/building_openssl_with_visual_studio_2013.html
            self.run_in_src(r"ms\do_nasm")
        else:
            if arch == "64A":
                self.run_in_src(r"ms\do_win64a")
            else:
                self.run_in_src(r"ms\do_ms")
        runtime = self.settings.compiler.runtime

        # Replace runtime in ntdll.mak and nt.mak
        def replace_runtime_in_file(filename):
            runtimes = ["MDd", "MTd", "MD", "MT"]
            for e in runtimes:
                try:
                    tools.replace_in_file(filename, "/%s" % e, "/%s" % runtime)
                    self.output.warn("replace vs runtime %s in %s" % ("/%s" % e, filename))
                    return  # we found a runtime argument in the file, so we can exit the function
                except:
                    pass
            raise Exception("Could not find any vs runtime in file")

        replace_runtime_in_file("./%s/ms/ntdll.mak" % self.subfolder)
        replace_runtime_in_file("./%s/ms/nt.mak" % self.subfolder)
        if self.settings.arch == "x86":  # Do not consider warning as errors, 1.0.2n error with x86 builds
            tools.replace_in_file("./%s/ms/nt.mak" % self.subfolder, "-WX", "")
            tools.replace_in_file("./%s/ms/ntdll.mak" % self.subfolder, "-WX", "")

        make_command = "nmake -f ms\\ntdll.mak" if self.options.shared else "nmake -f ms\\nt.mak "
        self.output.warn("----------MAKE OPENSSL %s-------------" % self.version)
        self.run_in_src(make_command)
        self.run_in_src("%s install" % make_command)
        # Rename libs with the arch
        renames = {"./binaries/lib/libeay32.lib": "./binaries/lib/libeay32%s.lib" % runtime,
                    "./binaries/lib/ssleay32.lib": "./binaries/lib/ssleay32%s.lib" % runtime}
        for old, new in renames.items():
            if os.path.exists(old):
                os.rename(old, new)

    def visual_build(self, config_options_string):
        # Will output binaries to ./binaries
        with tools.vcvars(self.settings, filter_known_paths=False):
            if self.settings.compiler.toolset in ["v110_xp", "v120_xp", "v140_xp", "v141_xp"]:
                # https://blogs.msdn.microsoft.com/vcblog/2012/10/08/windows-xp-targeting-with-c-in-visual-studio-2012/
                xpToolsetPath = tools.get_env("ProgramFiles(x86)") + "\\Microsoft SDKs\\Windows\\v7.1A\\"
                path = xpToolsetPath + "Bin;" + tools.get_env("PATH")
                include = xpToolsetPath + "Include;" + tools.get_env("INCLUDE")
                lib = xpToolsetPath + "Lib;" + tools.get_env("LIB")
                cl = "/D_USING_V110_SDK71_;" + tools.get_env("CL", default="")
                link = "/SUBSYSTEM:CONSOLE,5.01 " + tools.get_env("LINK", default="")

                if self.settings.arch == "x86_64":
                    lib = xpToolsetPath + "Lib\\x64;" + tools.get_env("LIB")
                    link = "/SUBSYSTEM:CONSOLE,5.02 " + tools.get_env("LINK", default="")
                elif self.settings.arch != "x86":
                    raise Exception("Architecture not set")

                with tools.environment_append({"PATH": path, "INCLUDE": include, "LIB": lib, "CL": cl, "LINK": link}):
                    self.visual_build_(config_options_string)
            else:
                self.visual_build_(config_options_string)
                
            

    def mingw_build(self, config_options_string):
        # https://netix.dl.sourceforge.net/project/msys2/Base/x86_64/msys2-x86_64-20161025.exe
        config_options_string = tools.unix_path(config_options_string)
        if self.settings.build_type == "Debug":
            config_options_string = "-g " + config_options_string
        if self.settings.arch == "x86":
            config_line = "./Configure mingw %s" % config_options_string
        else:
            config_line = "./Configure mingw64 %s" % config_options_string
        self.output.warn(config_line)
        with tools.chdir(self.subfolder):
            tools.run_in_windows_bash(self, config_line)
            self.output.warn("----------MAKE OPENSSL %s-------------" % self.version)
            # tools.run_in_windows_bash(self, "make depend")
            tools.run_in_windows_bash(self, "make")

    def package(self):
        # Copy the license files
        self.copy("%s/LICENSE" % self.subfolder, keep_path=False)
        self.copy(pattern="*applink.c", dst="include/openssl/", keep_path=False)
        if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            self._copy_visual_binaries()
            self.copy(pattern="*.h", dst="include/openssl/", src="binaries/include/", keep_path=False)
        elif self.settings.os == "Windows" and self.settings.compiler == "gcc":
            self.copy(pattern="%s/include/*" % self.subfolder, dst="include/openssl/", keep_path=False)
            if self.options.shared:
                self.copy(pattern="%s/libcrypto.dll.a" % self.subfolder, dst="lib", keep_path=False)
                self.copy(pattern="%s/libssl.dll.a" % self.subfolder, dst="lib", keep_path=False)
                self.copy(pattern="%s/libeay32.dll" % self.subfolder, dst="bin", keep_path=False)
                self.copy(pattern="%s/ssleay32.dll" % self.subfolder, dst="bin", keep_path=False)
            else:
                self.copy(pattern="%s/libcrypto.a" % self.subfolder, dst="lib", keep_path=False)
                self.copy(pattern="%s/libssl.a" % self.subfolder, dst="lib", keep_path=False)
        else:
            if self.options.shared:
                self.copy(pattern="*libcrypto*.dylib", dst="lib", keep_path=False)
                self.copy(pattern="*libssl*.dylib", dst="lib", keep_path=False)
                self.copy(pattern="*libcrypto.so*", dst="lib", keep_path=False)
                self.copy(pattern="*libssl.so*", dst="lib", keep_path=False)
            else:
                self.copy("*.a", "lib", keep_path=False)
            self.copy(pattern="%s/include/*" % self.subfolder, dst="include/openssl/", keep_path=False)

    def _copy_visual_binaries(self):
        self.copy(pattern="*.lib", dst="lib", src="binaries/lib", keep_path=False)
        self.copy(pattern="*.dll", dst="bin", src="binaries/bin", keep_path=False)
        self.copy(pattern="*.dll", dst="bin", src="binaries/bin", keep_path=False)

        suffix = str(self.settings.compiler.runtime)
        lib_path = os.path.join(self.package_folder, "lib")
        current_ssleay = os.path.join(lib_path, "ssleay32%s.lib" % suffix)
        current_libeay = os.path.join(lib_path, "libeay32%s.lib" % suffix)
        os.rename(current_ssleay, os.path.join(lib_path, "ssleay32.lib"))
        os.rename(current_libeay, os.path.join(lib_path, "libeay32.lib"))

    def package_info(self):
        if self.settings.compiler == "Visual Studio":
            self.cpp_info.libs = ["ssleay32", "libeay32", "crypt32", "msi", "ws2_32"]
        elif self.settings.compiler == "gcc" and self.settings.os == "Windows":
            self.cpp_info.libs = ["ssl", "crypto", "ws2_32"]
            if not self.options.shared:
                self.cpp_info.libs.extend(["crypt32", "gdi32"])
        elif self.settings.os == "Linux":
            self.cpp_info.libs = ["ssl", "crypto", "dl"]
        else:
            self.cpp_info.libs = ["ssl", "crypto"]
