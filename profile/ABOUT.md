The terminal card is inspired by [Andrew6rant's profile](https://github.com/Andrew6rant/Andrew6rant). Its generator and layout are written for Etticx; the ASCII portrait comes from Etticx's current GitHub avatar.

Edit `config.json` for biography/contact text and `avatar.txt` for the portrait. Run `python3 scripts/update_profile.py` to fetch public statistics, or add `--offline` to render the saved snapshot. The generator uses Python's standard library.

The workflow refreshes daily at 02:41 UTC (10:41 in Malaysia), on manual dispatch, and when its source/configuration changes on main. GitHub may delay scheduled runs. GitHub's built-in `GITHUB_TOKEN` supplies the required API and repository access; no personal access token or custom secrets are needed. The first refresh runs when the pull request is merged.

Statistics have explicit public scopes: repositories are public repositories owned by Etticx (including forks); stars are summed across public repositories owned by Etticx excluding forks; commits are public indexed results from GitHub commit search for `author:Etticx is:public`, which can differ from the contribution calendar and does not represent every commit ever authored; followers come from the public account. No private repository data is requested or published. An incomplete commit-search response fails the update and preserves the previous cards.

README image paths are relative, so the images work on the pull request branch as well as on the live profile after merging. The existing Bomberman and 3D contribution workflows are independent.
