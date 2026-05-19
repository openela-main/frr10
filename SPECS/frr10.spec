%global frr_libdir %{_libexecdir}/frr
%global build_name frr

%global _hardened_build 1
%define _legacy_common_support 1
%global selinuxtype targeted
%bcond_without selinux

Name: frr10
Version: 10.4.1
Release: 3%{?checkout}%{?dist}
Summary: Routing daemon
License: GPLv2+
URL: http://www.frrouting.org
Source0: https://github.com/FRRouting/frr/releases/download/%{build_name}-%{version}/%{build_name}-%{version}.tar.gz
Source1: %{build_name}-tmpfiles.conf
Source2: frr-sysusers.conf
Source3: frr.fc
Source4: frr.te
Source5: frr.if
Source6: remove-babeld-ldpd.sh
BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  bison >= 2.7
BuildRequires:  c-ares-devel
BuildRequires:  flex
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  git-core
BuildRequires:  groff
BuildRequires:  json-c-devel
BuildRequires:  libcap-devel
BuildRequires:  libtool
BuildRequires:  libyang-devel >= 2.0.0
BuildRequires:  make
BuildRequires:  ncurses
BuildRequires:  ncurses-devel
BuildRequires:  net-snmp-devel
BuildRequires:  pam-devel
BuildRequires:  patch
BuildRequires:  perl-XML-LibXML
BuildRequires:  perl-generators
BuildRequires:  python3-devel
BuildRequires:  python3-pytest
BuildRequires:  python3-sphinx
BuildRequires:  readline-devel
BuildRequires:  systemd-devel
BuildRequires:  systemd-rpm-macros
BuildRequires:  texinfo
BuildRequires:  protobuf-c-devel

Requires: net-snmp
Requires: ncurses
Requires(post): systemd
Requires(post): /sbin/install-info
Requires(post): hostname
Requires(preun): systemd
Requires(preun): /sbin/install-info
Requires(postun): systemd

%if 0%{?with_selinux}
Requires: (%{name}-selinux = %{version}-%{release} if selinux-policy-%{selinuxtype})
%endif

Conflicts: quagga
Conflicts: frr
Provides: routingdaemon = %{version}-%{release}

Patch0000: 0000-remove-babeld-and-ldpd.patch
Patch0002: 0002-enable-openssl.patch
Patch0003: 0003-disable-eigrp-crypto.patch
Patch0004: 0004-fips-mode.patch
# Turn off one fuzz test that fails with the new glibc
Patch0014: 0014-isisd-fuzz-test.patch

%description
FRRouting is free software that manages TCP/IP based routing protocols. It takes
a multi-server and multi-threaded approach to resolve the current complexity
of the Internet.

FRRouting supports BGP4, OSPFv2, OSPFv3, ISIS, RIP, RIPng, PIM, NHRP, PBR, EIGRP and BFD.

FRRouting is a fork of Quagga.

%if 0%{?with_selinux}
%package selinux
Summary:        Selinux policy for FRR
BuildArch:      noarch
Requires:       selinux-policy-%{selinuxtype}
Requires(post): selinux-policy-%{selinuxtype}
BuildRequires:  selinux-policy-devel
Conflicts:      frr-selinux
%{?selinux_requires}

%description selinux
SELinux policy modules for FRR package

%endif

%prep
%autosetup -S git -n frr-%{version}
mkdir selinux
cp -p %{SOURCE3} %{SOURCE4} %{SOURCE5} selinux

%build
# This is needed to pass a build with the new glibc
# but this could affect the speed of inet_ntop calls
# https://github.com/FRRouting/frr/issues/18575
export CFLAGS="%{optflags} -DINET_NTOP_NO_OVERRIDE"
autoreconf -ivf

%configure \
    --sbindir=%{frr_libdir} \
    --sysconfdir=%{_sysconfdir}/frr \
    --libdir=%{_libdir}/frr \
    --libexecdir=%{_libexecdir}/frr \
    --localstatedir=%{_localstatedir}/run/frr \
    --enable-multipath=64 \
    --enable-vtysh=yes \
    --disable-ospfclient \
    --disable-ospfapi \
    --enable-snmp=agentx \
    --enable-user=frr \
    --enable-group=frr \
    --enable-vty-group=frrvty \
    --enable-rtadv \
    --disable-exampledir \
    --enable-systemd=yes \
    --enable-static=no \
    --disable-ldpd \
    --disable-babeld \
    --with-moduledir=%{_libdir}/frr/modules \
    --with-crypto=openssl \
    --enable-fpm

%make_build MAKEINFO="makeinfo --no-split" PYTHON=%{__python3}

pushd doc
make info
popd

%if 0%{?with_selinux}
make -C selinux -f %{_datadir}/selinux/devel/Makefile %{build_name}.pp
bzip2 -9 selinux/%{build_name}.pp
%endif

%install
mkdir -p %{buildroot}/etc/{frr,rc.d/init.d,sysconfig,logrotate.d,pam.d,default} \
         %{buildroot}/var/log/frr %{buildroot}%{_infodir} \
         %{buildroot}%{_unitdir}

mkdir -p -m 0755 %{buildroot}%{_libdir}/frr
mkdir -p %{buildroot}%{_tmpfilesdir}

%make_install

# Remove this file, as it is uninstalled and causes errors when building on RH9
rm -rf %{buildroot}/usr/share/info/dir

install -p -m 644 %{SOURCE1} %{buildroot}%{_tmpfilesdir}/%{build_name}.conf
install -p -m 644 tools/etc/frr/daemons %{buildroot}/etc/frr/daemons
install -p -m 644 tools/frr.service %{buildroot}%{_unitdir}/frr.service
install -p -m 755 tools/frrinit.sh %{buildroot}%{frr_libdir}/frr
install -p -m 755 tools/frrcommon.sh %{buildroot}%{frr_libdir}/frrcommon.sh
install -p -m 755 tools/watchfrr.sh %{buildroot}%{frr_libdir}/watchfrr.sh

install -p -m 644 redhat/frr.logrotate %{buildroot}/etc/logrotate.d/frr
install -p -m 644 redhat/frr.pam %{buildroot}/etc/pam.d/frr
install -d -m 775 %{buildroot}/run/frr

install -p -D -m 0644 %{SOURCE2} ${RPM_BUILD_ROOT}/%{_sysusersdir}/frr.conf

%if 0%{?with_selinux}
install -D -m 644 selinux/%{build_name}.pp.bz2 \
        %{buildroot}%{_datadir}/selinux/packages/%{selinuxtype}/%{build_name}.pp.bz2
install -D -m 644 selinux/%{build_name}.if %{buildroot}%{_datadir}/selinux/devel/include/distributed/%{build_name}.if
%endif

# Delete libtool archives
find %{buildroot} -type f -name "*.la" -delete -print

#Upstream does not maintain a stable API, these headers from -devel subpackage are no longer needed
rm %{buildroot}%{_libdir}/frr/*.so
rm -r %{buildroot}%{_includedir}/frr/

%pre
%sysusers_create_compat %{SOURCE2}
exit 0

%post
%systemd_post frr.service

if [ -f %{_infodir}/%{build_name}.inf* ]; then
    install-info %{_infodir}/frr.info %{_infodir}/dir || :
fi

# Create dummy files if they don't exist so basic functions can be used.
# Only create frr.conf when first installing, otherwise it can change
# the behavior of the package
if [ $1 -eq 1 ]; then
    if [ ! -e %{_sysconfdir}/frr/frr.conf ]; then
        echo "hostname `hostname`" > %{_sysconfdir}/frr/frr.conf
        chown frr:frr %{_sysconfdir}/frr/frr.conf
        chmod 640 %{_sysconfdir}/frr/frr.conf
    fi
fi

#still used by vtysh, this way no error is produced when using vtysh
if [ ! -e %{_sysconfdir}/frr/vtysh.conf ]; then
    touch %{_sysconfdir}/frr/vtysh.conf
    chmod 640 %{_sysconfdir}/frr/vtysh.conf
    chown frr:frrvty %{_sysconfdir}/frr/vtysh.conf
fi


%postun
%systemd_postun_with_restart frr.service

%preun
%systemd_preun frr.service

#only when removing frr
if [ $1 -eq 0 ]; then
	if [ -f %{_infodir}/%{build_name}.inf* ]; then
    	install-info --delete %{_infodir}/frr.info %{_infodir}/dir || :
	fi
fi

%if 0%{?with_selinux}
%pre selinux
%selinux_relabel_pre -s %{selinuxtype}

%post selinux
%selinux_modules_install -s %{selinuxtype} %{_datadir}/selinux/packages/%{selinuxtype}/%{build_name}.pp.bz2
%selinux_relabel_post -s %{selinuxtype}
#/var/tmp and /var/run need to be relabeled as well if FRR is running before upgrade
if [ $1 == 2 ]; then
    %{_sbindir}/restorecon -R /var/tmp/frr &> /dev/null
    %{_sbindir}/restorecon -R /var/run/frr &> /dev/null
fi

%postun selinux
if [ $1 -eq 0 ]; then
    %selinux_modules_uninstall -s %{selinuxtype} %{build_name}
    %selinux_relabel_post -s %{selinuxtype}
fi
%endif

%check
make check PYTHON=%{__python3}

%files
%defattr(-,root,root)
%license COPYING
%doc doc/mpls
%dir %attr(750,frr,frr) %{_sysconfdir}/frr
%dir %attr(755,frr,frr) /var/log/frr
%dir %attr(755,frr,frr) /run/frr
%{_infodir}/*info*
%{_mandir}/man*/*
%dir %{frr_libdir}/
%{frr_libdir}/*
%{_bindir}/*
%dir %{_libdir}/frr
%{_libdir}/frr/*.so.*
%dir %{_libdir}/frr/modules
%{_libdir}/frr/modules/*
%config(noreplace) %attr(644,root,root) /etc/logrotate.d/frr
%config(noreplace) %attr(644,frr,frr) /etc/frr/daemons
%config(noreplace) /etc/pam.d/frr
%{_unitdir}/*.service
%dir /usr/share/yang
/usr/share/yang/*.yang
%{_tmpfilesdir}/%{build_name}.conf
%{_sysusersdir}/frr.conf

%if 0%{?with_selinux}
%files selinux
%{_datadir}/selinux/packages/%{selinuxtype}/%{build_name}.pp.*
%{_datadir}/selinux/devel/include/distributed/%{build_name}.if
%ghost %verify(not md5 size mode mtime) %{_sharedstatedir}/selinux/%{selinuxtype}/active/modules/200/%{build_name}
%endif

%changelog
* Fri Feb 06 2026 Michal Ruprich <mruprich@redhat.com> - 10.4.1-3
- Resolves: RHEL-147189 - AVC failures when running frr10

* Mon Dec 01 2025 Michal Ruprich <mruprich@redhat.com> - 10.4.1-2
- Enabling gating and testing, adding rpminspect.yaml

* Wed Nov 26 2025 Michal Ruprich <mruprich@redhat.com> - 10.4.1-1
- Initial commit on c9s
- Resolves: RHEL-125957 - Adding FRR10 as a versioned package
