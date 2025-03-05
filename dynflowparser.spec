Name:           python-dynflowparser
Version:        0.2.12
Release:        1%{?dist}
Summary:        Get sosreport dynflow files and generates user friendly html pages for tasks, plans, actions and steps

License:        None
URL:            https://github.com/pafernanr/dynflowparser
Source0:        %{pypi_source}
BuildArch:      noarch

BuildRequires:  python3-devel
# BuildRequires:  (python3dist(hacking) >= 6 with python3dist(hacking) < 6.2~~)
BuildRequires:  python3dist(jinja2)
# BuildRequires:  python3dist(pbr) >= 2
BuildRequires:  python3dist(pytz)
BuildRequires:  python3dist(setuptools)

%description
 dynflowparser Reads the dynflow files from a [sosreport]( and generates user
friendly html pages for Tasks, Plans, Actions and Steps. Companion command
dynflowparser-export-tasks helps to overcome sosreport file size limitations.
(Read [Limitations](limitations) below)- Only unsuccessful Tasks are parsed by
default. (Use '-a' to parse all). - Failed Actions & Steps are automatically
expanded...

%package -n     python3-dynflowparser
Summary:        %{summary}
%{?python_provide:%python_provide python3-dynflowparser}

Requires:       python3dist(jinja2)
Requires:       python3dist(pytz)
Requires:       python3dist(setuptools)
%description -n python3-dynflowparser
 dynflowparser Reads the dynflow files from a [sosreport]( and generates user
friendly html pages for Tasks, Plans, Actions and Steps. Companion command
dynflowparser-export-tasks helps to overcome sosreport file size limitations.
(Read [Limitations](limitations) below)- Only unsuccessful Tasks are parsed by
default. (Use '-a' to parse all). - Failed Actions & Steps are automatically
expanded...


%prep
%autosetup -n dynflowparser-%{version}
# Remove bundled egg-info
rm -rf dynflowparser.egg-info

%build
%py3_build

%install
%py3_install

%check
%{__python3} setup.py test

%files -n python3-dynflowparser
%license LICENSE
%doc README.md
%{_bindir}/dynflowparser
%{_bindir}/dynflowparser-export-tasks
%{python3_sitelib}/dynflowparser
%{python3_sitelib}/dynflowparserexport
%{python3_sitelib}/dynflowparser-%{version}-py%{python3_version}.egg-info

%changelog
* Wed Mar 05 2025 Pablo Fernández Rodríguez <pafernan@redhat.com> - 0.2.1-1
- Initial package.