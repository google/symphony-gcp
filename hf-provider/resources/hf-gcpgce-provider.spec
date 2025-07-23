Name: hf-gcpgce-provider
Version: 1.0.0
Release: %{getenv:GITHUB_RUN_NUMBER}%{?dist}
Summary: IBM Symphony Host Factory provider for GCP GCE
License: Apache2

Requires: bash
BuildArch: x86_64
BuildRoot: ~/rpmbuild/
Prefix: /opt/ibm/spectrumcomputing

%define _build_id_links none

%description
IBM Symphony Host Factory provider for GCP GCE

%install
echo "BUILDROOT = $RPM_BUILD_ROOT"
mkdir -p ${RPM_BUILD_ROOT}%{prefix}/hostfactory
cp -a ${GITHUB_WORKSPACE}/hf-provider/resources/gce_cli/* ${RPM_BUILD_ROOT}%{prefix}/hostfactory/
cp -a ${GITHUB_WORKSPACE}/hf-provider/dist/hf-gce ${RPM_BUILD_ROOT}%{prefix}/hostfactory/1.2/providerplugins/gcpgce/bin/
exit

%files
%dir %{prefix}/hostfactory
%attr(0755, root, root) %dir %{prefix}/hostfactory/1.2
%attr(0755, root, root) %dir %{prefix}/hostfactory/1.2/providerplugins
%dir %{prefix}/hostfactory/1.2/providerplugins/gcpgce
%dir %{prefix}/hostfactory/1.2/providerplugins/gcpgce/bin
%dir %{prefix}/hostfactory/1.2/providerplugins/gcpgce/scripts
%attr(0755, egoadmin, egoadmin) %{prefix}/hostfactory/1.2/providerplugins/gcpgce/bin/hf-gce
%attr(0644, egoadmin, egoadmin) %{prefix}/hostfactory/1.2/providerplugins/gcpgce/bin/README.md
%attr(0755, egoadmin, egoadmin) %{prefix}/hostfactory/1.2/providerplugins/gcpgce/scripts/*
%dir %{prefix}/hostfactory/conf
%dir %{prefix}/hostfactory/conf/providers
%dir %{prefix}/hostfactory/conf/providers/gcpgceinst
%attr(0644, egoadmin, egoadmin) %{prefix}/hostfactory/conf/providers/gcpgceinst/*

%changelog
