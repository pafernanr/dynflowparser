Name: dynflowparserng
Version: 0.0.0
Release: py3
Summary: Get sosreport dynflow files and generates user friendly html pages for tasks, plans, actions and steps

License: GPLv3
URL:            https://github.com/pafernanr/dynflowparserng
Source0: https://github.com/pafernanr/%{name}-%{version}.tar.gz
Group: Applications/System
BuildArch: noarch

BuildRoot: %{_tmppath}/%{name}-buildroot
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
Requires: python3-jinja2
Requires: python3-pytz

%description
Read sosreport dynflow files and generates user friendly html pages for Tasks, Plans, Actions and Steps

%prep
%setup -qn %{name}-%{version}

%build

%install
rm -rf ${RPM_BUILD_ROOT}

mkdir -p ${RPM_BUILD_ROOT}/usr/lib/tools/dynflowparserng/bin
install -D -m 755 dynflowparserng/bin/__init__.py ${RPM_BUILD_ROOT}/usr/lib/tools/dynflowparserng/bin/__init__.py
mkdir -p ${RPM_BUILD_ROOT}/usr/lib/tools/dynflowparserng_export_tasks/bin
install -D -m 755 dynflowparserng_export_tasks/bin/__init__.py ${RPM_BUILD_ROOT}/usr/lib/tools/dynflowparserng_export_tasks/bin/__init__.py
cp -rp dynflowparserng ${RPM_BUILD_ROOT}/usr/lib/tools/
cp -rp dynflowparserng_export_tasks ${RPM_BUILD_ROOT}/usr/lib/tools/

rm -rf ${RPM_BUILD_ROOT}/usr/lib/tools/%{name}/lib/__pycache__

%post
ln -s -f /usr/lib/tools/dynflowparserng/bin/__init__.py /usr/bin/dynflowparserng
ln -s -f /usr/lib/tools/dynflowparserng_export_tasks/bin/__init__.py /usr/bin/dynflowparserng-export-tasks

%postun
if [ $1 -eq 0 ] ; then
    rm -f /usr/bin/%{name}
    rm -f /usr/bin/export-tasks
fi

%clean
rm -rf ${RPM_BUILD_ROOT}

%files
%defattr(-,root,root,-)
/usr/lib/tools/dynflowparserng
/usr/lib/tools/dynflowparserng_export_tasks
