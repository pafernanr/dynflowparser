%define _unpackaged_files_terminate_build 0

Name:           dynflowparser
Version:        0.0.0
Release:        1-%{dist}
Summary:        Get sosreport dynflow files and generates user friendly html pages for tasks, plans, actions and steps

License:        None
URL:            https://github.com/pafernanr/dynflowparser
Source0: https://github.com/pafernanr/%{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires: python3-devel
BuildRequires: python3-setuptools
Requires: python3dist(jinja2)
Requires: python3dist(pytz)

%description
Dynflowparser reads the dynflow files from a `sosreport` and generates user
friendly html pages for Tasks, Plans, Actions and Steps. Companion command
`dynflowparser_export_tasks` helps to overcome sosreport 100Mb file size limit.

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
%pyproject_save_files dynflowparser_export_tasks
%else
%py3_install
%endif

%files
%{_bindir}/dynflowparser
%{_bindir}/dynflowparser_export_tasks
%license LICENSE
%doc README.md
%{python3_sitelib}/dynflowparser
%{python3_sitelib}/dynflowparser_export_tasks
