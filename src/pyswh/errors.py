class SwhSaveError(Exception):
    """
    Error during the saving of code in the Software Heritage Archive.
    Raised by :meth:`~pyswh.swh.save`.
    """
    pass
