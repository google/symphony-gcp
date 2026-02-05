Name: hf-gcpgke-provider
Version: 1.0.0
Release: %{getenv:GITHUB_RUN_NUMBER}%{?dist}
Summary: IBM Symphony Host Factory provider for GCP GKE
License: Apache2

Requires: bash
BuildArch: x86_64
BuildRoot: ~/rpmbuild/
Prefix: /opt/ibm/spectrumcomputing

%define _build_id_links none

%description
IBM Symphony Host Factory provider for GCP GKE

%install
echo "BUILDROOT = $RPM_BUILD_ROOT"
mkdir -p ${RPM_BUILD_ROOT}%{prefix}/hostfactory
cp -a ${GITHUB_WORKSPACE}/hf-provider/resources/gke_cli/* ${RPM_BUILD_ROOT}%{prefix}/hostfactory/
cp -a ${GITHUB_WORKSPACE}/hf-provider/dist/hf-gke ${RPM_BUILD_ROOT}%{prefix}/hostfactory/1.2/providerplugins/gcpgke/bin/
exit

%files
%dir %{prefix}/hostfactory
%attr(0755, root, root) %dir %{prefix}/hostfactory/1.2
%attr(0755, root, root) %dir %{prefix}/hostfactory/1.2/providerplugins
%dir %{prefix}/hostfactory/1.2/providerplugins/gcpgke
%dir %{prefix}/hostfactory/1.2/providerplugins/gcpgke/bin
%dir %{prefix}/hostfactory/1.2/providerplugins/gcpgke/scripts
%attr(0755, egoadmin, egoadmin) %{prefix}/hostfactory/1.2/providerplugins/gcpgke/bin/hf-gke
%attr(0755, egoadmin, egoadmin) %{prefix}/hostfactory/1.2/providerplugins/gcpgce/bin/show_gke_provider_install.sh
%attr(0644, egoadmin, egoadmin) %{prefix}/hostfactory/1.2/providerplugins/gcpgke/bin/README.md
%attr(0755, egoadmin, egoadmin) %{prefix}/hostfactory/1.2/providerplugins/gcpgke/scripts/*
%dir %{prefix}/hostfactory/conf
%dir %{prefix}/hostfactory/conf/providers
%dir %{prefix}/hostfactory/conf/providers/gcpgkeinst
%attr(0644, egoadmin, egoadmin) %{prefix}/hostfactory/conf/providers/gcpgkeinst/*

%changelog
