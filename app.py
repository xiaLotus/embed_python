import pkg_resources

installed_packages = pkg_resources.working_set
for dist in sorted(installed_packages, key=lambda x: x.project_name.lower()):
    print(f"{dist.project_name}=={dist.version}")