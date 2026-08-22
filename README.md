# aerynos_packages

My collection of [AerynOS](https://aerynos.com/) packages — recipes for things that
are not (yet) in the distribution's own [recipes](https://github.com/AerynOS/recipes)
repository.

| Package | Version | Summary |
| --- | --- | --- |
| [`apparmor`](a/apparmor) | 5.0.2 | Mandatory access control based on per-program profiles |
| [`cosmic-ext-applet-package-updater`](c/cosmic-ext-applet-package-updater) | 1.0.0+git | COSMIC panel applet notifying about package updates, with moss support |
| [`efibootmgr`](e/efibootmgr) | 18 | Manipulate the UEFI boot manager configuration |
| [`efivar`](e/efivar) | 39 | Tools and library to manipulate EFI variables |
| [`fio`](f/fio) | 3.42 | Flexible I/O tester |
| [`fwupd`](f/fwupd) | 2.1.7 | Firmware update daemon |
| [`geteltorito`](g/geteltorito) | 0.6 | El Torito boot image extractor |
| [`ipset`](i/ipset) | 7.24 | Administration tool for IP sets |
| [`mandoc`](m/mandoc) | 1.14.6 | Formatter for BSD mdoc and man documentation |
| [`modemmanager`](m/modemmanager) | 1.24.2 | Mobile broadband modem management daemon |
| [`nec2c`](n/nec2c) | 1.3.3 | NEC2 antenna modelling engine translated to C |
| [`nvme-cli`](n/nvme-cli) | 2.16 | NVM Express user space tooling |
| [`passim`](p/passim) | 0.1.12 | Local caching server for shared metadata |
| [`python-beniget`](p/python-beniget) | 0.4.2.post1 | Static analysis of Python code, needed by pythran |
| [`python-gast`](p/python-gast) | 0.6.0 | Version-agnostic Python AST, needed by pythran |
| [`python-hypothesis`](p/python-hypothesis) | 6.165.5 | Property-based testing for Python, needed by the numpy and scipy suites |
| [`python-jinja2`](p/python-jinja2) | 3.1.6 | Template engine for Python, needed to build fwupd |
| [`python-numpy`](p/python-numpy) | 2.5.2 | Fundamental package for scientific computing with Python |
| [`python-pyserial`](p/python-pyserial) | 3.5 | Serial port access for Python |
| [`python-scipy`](p/python-scipy) | 1.18.0 | Fundamental algorithms for scientific computing in Python |
| [`python-sortedcontainers`](p/python-sortedcontainers) | 2.4.0 | Sorted list, dict and set implementations, needed by hypothesis |
| [`pythran`](p/pythran) | 0.18.1 | Ahead of time compiler for numeric Python kernels |
| [`reaction`](r/reaction) | 2.5.1 | Scans program output for repeated patterns and takes action (a fail2ban successor) |
| [`sdrplay-api`](s/sdrplay-api) | 3.15.2 | SDRplay RSP API library and service (proprietary) |
| [`sedutil`](s/sedutil) | 1.20.0+git | Manage TCG Opal self-encrypting drives |
| [`soapysdr`](s/soapysdr) | 0.8.1 | Vendor neutral SDR support library |
| [`soapysdrplay3`](s/soapysdrplay3) | 0.5.2 | SoapySDR module for SDRplay RSP receivers |
| [`tpm2-abrmd`](t/tpm2-abrmd) | 3.0.0 | TPM2 access broker and resource manager daemon |
| [`tpm2-tools`](t/tpm2-tools) | 5.8 | Command line tools for the TPM 2.0 software stack |
| [`ufw`](u/ufw) | 0.36.2 | Uncomplicated Firewall, a front-end for Netfilter |
| [`wch-ble-extcap`](w/wch-ble-extcap) | 0.1.1 | Wireshark extcap plugin for the WCH BLE Analyzer Pro |
| [`wtype`](w/wtype) | 0.4 | xdotool type for Wayland |
| [`xnec2c`](x/xnec2c) | 4.4.18 | Graphical NEC2 antenna simulator |

Deliberately *not* here: `wine`. AerynOS already ships it, currently 11.15, and
already builds it with new WoW64 (`--enable-archs=i386,x86_64`) so it runs
32-bit Windows programs without 32-bit host libraries. A recipe under this
repository would install at priority 10 and shadow the distribution's, which
means hand-maintaining a version bump roughly every fortnight to stay level with
it. If a genuinely different build is ever wanted, `wine-staging` is the thing
to package, under its own name so that it coexists rather than shadows.

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
    --repo name=unstable,base-uri=https://cdn.aerynos.dev/,channel=main,version=stream/unstable,priority=0 \
    --repo name=local,uri=file:///home/dc0sk/git/aerynos_packages/local/x86_64/stone.index,priority=10

scripts/local-repo.sh p/python-jinja2       # build and index the dependency first
boulder build -p local-x86_64 f/fwupd/stone.yaml
```

The stock repository in that profile should name the same stream the machine
itself is subscribed to, which `moss repo list` will report. They are separate
settings and nothing warns when they drift: builds would resolve against one set
of packages while the system runs another. boulder's own `default-x86_64`
profile is on `stream/volatile`, so it is not a safe thing to copy blindly.

boulder has no command to edit or remove a profile once created - `profile
update` only refetches what a profile already points at. To change one, edit
`~/.config/boulder/profile.d/<name>.kdl` directly and then run `boulder profile
update -y -p <name>`.

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
