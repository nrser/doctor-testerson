Doctor Testerson (Dr. T)
==============================================================================

Provides a stupid little `dr.t` command to run Python doctests.

How To...
------------------------------------------------------------------------------

### Publish ###

1.  Update the version in `pyproject.toml`.
    
2.  Commit, tag `vX.Y.Z`, push.
    
3.  Log in to [PyPI](https://pypi.org) and go to
    
    https://pypi.org/manage/account/
    
    to generate an API token.
    
4.  Throw `poetry` at it:
    
        poetry publish --build --username __token__ --password <token>
    
5.  Bump patch by 1 and append `-dev`, commit and push (now we're on the "dev"
    version of the next patch version).
