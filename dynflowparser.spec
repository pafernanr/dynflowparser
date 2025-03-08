Name: dynflowparser
Version: 0.0.0
Release: py3
Summary: Get sosreport dynflow files and generates user friendly html pages for tasks, plans, actions and steps

License: GPLv3
URL:            https://github.com/pafernanr/dynflowparser
Source0: https://github.com/pafernanr/%{name}-%{version}.tar.gz
Group: Applications/System
BuildArch: noarch

BuildRoot: %{_tmppath}/%{name}-buildroot
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
Requires: python3-jinja2
Requires: python3-dateutil

%description
Read sosreport dynflow files and generates user friendly html pages for Tasks, Plans, Actions and Steps

%prep
%setup -qn %{name}-%{version}

%build

%install
rm -rf ${RPM_BUILD_ROOT}

mkdir -p ${RPM_BUILD_ROOT}/usr/lib/tools/dynflowparser/bin
install -D -m 755 dynflowparser/bin/dynflowparser ${RPM_BUILD_ROOT}/usr/lib/tools/dynflowparser/bin/dynflowparser
mkdir -p ${RPM_BUILD_ROOT}/usr/lib/tools/dynflowparser_export_tasks/bin
install -D -m 755 dynflowparser_export_tasks/bin/dynflowparser-export-tasks ${RPM_BUILD_ROOT}/usr/lib/tools/dynflowparser_export_tasks/bin/dynflowparser-export-tasks
cp -rp dynflowparser ${RPM_BUILD_ROOT}/usr/lib/tools/
cp -rp dynflowparser_export_tasks ${RPM_BUILD_ROOT}/usr/lib/tools/

rm -rf ${RPM_BUILD_ROOT}/usr/lib/tools/%{name}/lib/__pycache__
rm -rf ${RPM_BUILD_ROOT}/usr/lib/tools/%{name}/html/images

%post
ln -s -f /usr/lib/tools/dynflowparser/bin/dynflowparser /usr/bin/dynflowparser
ln -s -f /usr/lib/tools/dynflowparser_export_tasks/bin/dynflowparser-export-tasks /usr/bin/dynflowparser-export-tasks

%postun
if [ $1 -eq 0 ] ; then
    rm -f /usr/bin/%{name}
    rm -f /usr/bin/export-tasks
fi

%clean
rm -rf ${RPM_BUILD_ROOT}

%files
%defattr(-,root,root,-)
/usr/lib/tools/dynflowparser
/usr/lib/tools/dynflowparser_export_tasks
