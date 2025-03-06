%define _unpackaged_files_terminate_build 0

Name:           dynflowparser
Version:        0.2.19
Release:        1%{?dist}
Summary:        Get sosreport dynflow files and generates user friendly html pages for tasks, plans, actions and steps

License:        None
URL:            https://github.com/pafernanr/dynflowparser
Source0: https://github.com/pafernanr/%{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires: python3-devel
# BuildRequires: python3dist(wheel)
%if 0%{?rhel} && 0%{?rhel} < 10
BuildRequires: python3-setuptools
%else
BuildRequires: python3-packaging
%endif
Requires: python3dist(jinja2)
Requires: python3dist(pytz)

%description
Dynflowparser reads the dynflow files from a `sosreport` and generates user
friendly html pages for Tasks, Plans, Actions and Steps. Companion command
`dynflowparser-export-tasks` helps to overcome sosreport 100Mb file size limit.

%prep
%setup -qn %{name}-%{version}

%if 0%{?fedora} >= 39
%generate_buildrequires
%pyproject_buildrequires
%endif

%build
%if 0%{?fedora} >= 39
%pyproject_wheel
%else
%py3_build
%endif

%install
%if 0%{?fedora} >= 39
%pyproject_install
%pyproject_save_files dynflowparser
%pyproject_save_files dynflowparserexport
%else
%py3_install
%endif

%files
%{_bindir}/dynflowparser
%{_bindir}/dynflowparser-export-tasks
%license LICENSE
%doc README.md
%{python3_sitelib}/dynflowparser
%{python3_sitelib}/dynflowparserexport
%{python3_sitelib}/%{name}-%{version}.dist-info
