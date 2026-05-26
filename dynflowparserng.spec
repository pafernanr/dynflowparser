Name:           dynflowparserng
Version:        0.0.0
Release:        1%{?dist}
Summary:        Get sosreport dynflow files and generates user friendly html pages

License:        GPLv3
URL:            https://github.com/pafernanr/dynflowparserng
Source0:        https://github.com/pafernanr/%{name}/archive/v%{version}.tar.gz
BuildArch:      noarch

# Build dependencies
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

# Runtime dependencies
Requires:       python3-jinja2
Requires:       python3-pandas
Requires:       python3-pytz

%description
DynflowParserNG reads sosreport dynflow files and generates user friendly
HTML pages for Tasks, Plans, Actions and Steps. It helps analyze Foreman
Dynflow execution data from sosreports.

%prep
%autosetup -n %{name}-%{version}

%build
# Nothing to build - pure Python package

%install
mkdir -p %{buildroot}/usr/lib/tools/dynflowparserng/bin
mkdir -p %{buildroot}/usr/lib/tools/dynflowparserng_export_tasks/bin

# Install main package
install -D -m 755 dynflowparserng/bin/__init__.py \
    %{buildroot}/usr/lib/tools/dynflowparserng/bin/__init__.py

# Install export tasks package
install -D -m 755 dynflowparserng_export_tasks/bin/__init__.py \
    %{buildroot}/usr/lib/tools/dynflowparserng_export_tasks/bin/__init__.py

# Copy package directories
cp -rp dynflowparserng %{buildroot}/usr/lib/tools/
cp -rp dynflowparserng_export_tasks %{buildroot}/usr/lib/tools/

# Clean up __pycache__ directories
find %{buildroot}/usr/lib/tools/%{name} -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find %{buildroot}/usr/lib/tools/dynflowparserng_export_tasks -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

%post
ln -sf /usr/lib/tools/dynflowparserng/bin/__init__.py /usr/bin/dynflowparserng
ln -sf /usr/lib/tools/dynflowparserng_export_tasks/bin/__init__.py /usr/bin/dynflowparserng-export-tasks

%postun
if [ $1 -eq 0 ] ; then
    rm -f /usr/bin/dynflowparserng
    rm -f /usr/bin/dynflowparserng-export-tasks
fi

%files
%license LICENSE
%doc README.md AUTHORS
/usr/lib/tools/dynflowparserng
/usr/lib/tools/dynflowparserng_export_tasks

%changelog
* Mon May 26 2025 Pablo Fernández Rodríguez <pfernanr@example.com> - 0.0.0-1
- Add pandas dependency for improved CSV parsing performance
- Add PRAGMA optimizations for SQLite operations
- Implement single transaction for better write performance
- Move index creation to after data insertion
- Reuse Jinja2 Environment for better HTML generation performance
- Add HTTP server and SSH tunnel support (--httpd-server, --ssh-tunnel)
- Apply Foreman theme to HTML output
- Add support for Satellite 6.19 (dynflow schema version 25)
- Enable text selection on task and action labels
- Initial RPM package release
