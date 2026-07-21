"""Generate ``docs/source/ZENODO.rst`` with the BibTeX entry for this version.

Run at documentation build time (see ``.readthedocs.yaml``). The Zenodo lookup
itself lives in the shared :mod:`zenodo` helper so it is not duplicated with the
release automation.
"""

import pathlib
import textwrap
import warnings

from zenodo import fetch_bibtex, find_record_for_version

import pedpy

zenodo_path = pathlib.Path("docs/source/ZENODO.rst")

zenodo_record = "If you use *PedPy* in your work, please cite it with the following information from Zenodo.\n\n"

try:
    record = find_record_for_version(pedpy.__version__)
    bibtex = fetch_bibtex(record.record_id)
    zenodo_record += ".. code-block:: bibtex\n\n" + textwrap.indent(bibtex, " " * 4) + "\n"
except Exception as e:  # docs build should not fail on Zenodo hiccups
    warnings.warn(f"An error occurred: {e}", stacklevel=2)

zenodo_record += textwrap.dedent(
    """\

        Information to all versions of PedPy can be found on `Zenodo <https://zenodo.org/doi/10.5281/zenodo.7194992>`_.

        .. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.7194992.svg
            :target: https://doi.org/10.5281/zenodo.7194992

        To find your installed version of *PedPy*, you can run:

        .. code-block:: bash

            import pedpy
            print(pedpy.__version__)
    """
)

with open(zenodo_path, "w") as f:
    f.write(zenodo_record)

print(zenodo_record)
