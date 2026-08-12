# aerynos_packages

My collection of [AerynOS](https://aerynos.com/) packages — recipes for things that
are not (yet) in the distribution's own [recipes](https://github.com/AerynOS/recipes)
repository.

| Package | Version | Summary |
| --- | --- | --- |
| [`fio`](f/fio) | 3.42 | Flexible I/O tester |
| [`fwupd`](f/fwupd) | 2.1.7 | Firmware update daemon |
| [`geteltorito`](g/geteltorito) | 0.6 | El Torito boot image extractor |
| [`nvme-cli`](n/nvme-cli) | 2.16 | NVM Express user space tooling |
| [`python-jinja2`](p/python-jinja2) | 3.1.6 | Template engine for Python, needed to build fwupd |
| [`reaction`](r/reaction) | 2.5.1 | Scans program output for repeated patterns and takes action (a fail2ban successor) |
| [`sedutil`](s/sedutil) | 1.20.0+git | Manage TCG Opal self-encrypting drives |
| [`tpm2-tools`](t/tpm2-tools) | 5.8 | Command line tools for the TPM 2.0 software stack |
| [`ufw`](u/ufw) | 0.36.2 | Uncomplicated Firewall, a front-end for Netfilter |

## Layout

Recipes follow the upstream AerynOS convention: one directory per package, filed
under its first letter.

```
<letter>/<name>/stone.yaml               the recipe
<letter>/<name>/monitoring.yaml          release-monitoring.org / CPE metadata
<letter>/<name>/manifest.x86_64.jsonc    build manifest, human readable
<letter>/<name>/manifest.x86_64.bin      build manifest, consumed by boulder
<letter>/<name>/pkg/                     files shipped by the package itself
```

## Building

A single package:

```sh
boulder build u/ufw/stone.yaml
```

### Packages that depend on other packages here

`fwupd` needs `python-jinja2` from this repository at build time, and boulder's
default profile only knows about the stock AerynOS repositories. Build against a
profile that also carries the local index:

```sh
boulder profile add local-x86_64 \
    --repo name=volatile,base-uri=https://cdn.aerynos.dev/,channel=main,version=stream/volatile,priority=0 \
    --repo name=local,uri=file:///home/dc0sk/git/aerynos_packages/local/x86_64/stone.index,priority=10

scripts/local-repo.sh p/python-jinja2       # build and index the dependency first
boulder build -p local-x86_64 f/fwupd/stone.yaml
```

The profile reads the index from disk each time, so re-running
`scripts/local-repo.sh` is enough to refresh what a build can see.

## Using these as a local repository

`scripts/local-repo.sh` builds every recipe into `local/$(uname -m)/` and generates
a moss index over the results:

```sh
scripts/local-repo.sh              # build everything, then index
scripts/local-repo.sh u/ufw        # build just one package, then index
scripts/local-repo.sh --index-only # re-index what is already built
```

boulder builds rootless, so that needs no privileges. Registering the index with
moss does, and is only needed once:

```sh
sudo moss repo add local file:///home/dc0sk/git/aerynos_packages/local/x86_64/stone.index -p 10
```

Priority 10 puts this repository above the stock ones (priority 0), so a local
build wins over an upstream package of the same name. From then on:

```sh
sudo moss sync            # pick up newly indexed builds
sudo moss install ufw
```

Re-running `scripts/local-repo.sh` after a recipe change is enough — moss reads
the index fresh each time. Note that a rebuilt package is only seen as an update
if the recipe's `release` was bumped.

The `local/` directory is git-ignored; nothing built ends up in version control.

## License

The recipes in this repository are MPL-2.0, matching AerynOS's own recipes. The
software they package is under its own respective license, recorded in each
recipe's `license` field.
