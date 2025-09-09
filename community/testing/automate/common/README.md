Common files are distributed using Symbolic links, paths are:

- `automate/modules/symphony/templates/scripts/common.sh`
- `automate/modules/symphony/nfs-server/common.sh`

The path for the common scripts is:

- `automate/common/common.sh`

> [!IMPORTANT]  
> Do not forget to use relative paths in relation to a common path.

```sh
cd $WORKDIR/automate/modules/symphony/templates/scripts/
ln -s ../../../../common/common.sh common.sh
cd $WORKDIR/automate/modules/symphony/nfs-server/
ln -s ../../../common/common.sh common.sh
```