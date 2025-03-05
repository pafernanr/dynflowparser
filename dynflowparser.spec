Name:           dynflowparser
Version:        0.1.9
Release:        1%{?dist}
Summary:        Get sosreport dynflow files and generates user friendly html pages for tasks, plans, actions and steps

License:        GPL-3.0
URL:            https://github.com/pafernanr/dynflowparser
Source0:        %{pypi_source}
BuildArch:      noarch

BuildRequires:  python3-devel
# BuildRequires:  python3dist(hacking)
BuildRequires:  python3dist(jinja2)
# BuildRequires:  python3dist(pbr) >= 2
BuildRequires:  python3dist(pytz)
BuildRequires:  python3dist(setuptools)

%description
%{name} Reads the dynflow files from a [sosreport]( and generates user
friendly html pages for Tasks, Plans, Actions and Steps. Companion command
dynflowparser-export-tasks helps to overcome sosreport file size limitations.
(Read [Limitations](limitations) below)- Only unsuccessful Tasks are parsed by
default. (Use '-a' to parse all). - Failed Actions & Steps are automatically
expanded...

%package -n     %{name}
Summary:        %{summary}
%{?python_provide:%python_provide %{name}}

Requires:       python3dist(jinja2)
Requires:       python3dist(pytz)
Requires:       python3dist(setuptools)
%description -n %{name}
 dynflowparser Reads the dynflow files from a [sosreport]( and generates user
friendly html pages for Tasks, Plans, Actions and Steps. Companion command
dynflowparser-export-tasks helps to overcome sosreport file size limitations.
(Read [Limitations](limitations) below)- Only unsuccessful Tasks are parsed by
default. (Use '-a' to parse all). - Failed Actions & Steps are automatically
expanded...


%prep
%autosetup -n %{name}
# Remove bundled egg-info
rm -rf dynflowparser.egg-info

%build
%py3_build

%install
%py3_install

%check
%{__python3} setup.py test

%files -n dynflowparser
%license LICENSE
%doc README.md
%{_bindir}/dynflowparser
%{_bindir}/dynflowparser-export-tasks
%{python3_sitelib}/dynflowparser
%{python3_sitelib}/dynflowparserexport
%{python3_sitelib}/%{name}-%{version}-py%{python3_version}.egg-info

