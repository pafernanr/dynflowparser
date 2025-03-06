# Created by pyp2rpm-3.3.10
%global pypi_name dynflowparser
%global pypi_version 0.2.18

Name:           python-%{pypi_name}
Version:        %{pypi_version}
Release:        1%{?dist}
Summary:        Get sosreport dynflow files and generates user friendly html pages for tasks, plans, actions and steps

License:        None
URL:            https://github.com/pafernanr/dynflowparser
Source0:        %{pypi_source}
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3dist(pbr) >= 2
BuildRequires:  python3dist(setuptools)

%description
 dynflowparser Reads the dynflow files from a [sosreport]( and generates user
friendly html pages for Tasks, Plans, Actions and Steps. Companion command
dynflowparser-export-tasks helps to overcome sosreport file size limitations.
(Read [Limitations](limitations) below)- Only unsuccessful Tasks are parsed by
default. (Use '-a' to parse all). - Failed Actions & Steps are automatically
expanded...

%package -n     python3-%{pypi_name}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{pypi_name}}

Requires:       python3dist(jinja2)
Requires:       python3dist(pytz)
Requires:       python3dist(setuptools)
%description -n python3-%{pypi_name}
 dynflowparser Reads the dynflow files from a [sosreport]( and generates user
friendly html pages for Tasks, Plans, Actions and Steps. Companion command
dynflowparser-export-tasks helps to overcome sosreport file size limitations.
(Read [Limitations](limitations) below)- Only unsuccessful Tasks are parsed by
default. (Use '-a' to parse all). - Failed Actions & Steps are automatically
expanded...


%prep
%autosetup -n %{pypi_name}-%{pypi_version}
# Remove bundled egg-info
rm -rf %{pypi_name}.egg-info

%build
%py3_build

%install
%py3_install

%files -n python3-%{pypi_name}
%license LICENSE
%doc README.md
%{_bindir}/dynflowparser
%{_bindir}/dynflowparser-export-tasks
%{python3_sitelib}/%{pypi_name}
%{python3_sitelib}/dynflowparserexport
%{python3_sitelib}/%{pypi_name}-%{pypi_version}-py%{python3_version}.egg-info
