# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import datetime
import os
import sys

basedir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "pedpy")
)
sys.path.insert(0, basedir)

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

current_year = datetime.datetime.today().year

project = "PedPy"
copyright = f"{current_year}, Forschungszentrum Jülich GmbH, IAS-7"
author = "Tobias Schrödter"
release = "1.0.0rc2"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.autosummary",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "autoapi.extension",
    "nbsphinx",
    "sphinx.ext.mathjax",
    "notfound.extension",
]

# automatic generation of api doc
autoapi_dirs = [
    "../../pedpy",
]
autoapi_root = "api"
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]
autoapi_ignore = ["**/tests/**"]
autoapi_member_order = ["groupwise"]
autoapi_python_use_implicit_namespaces = False


intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
intersphinx_disabled_domains = ["std"]

templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints"]

nbsphinx_allow_errors = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]

html_logo = "_static/logo_text.svg"
html_favicon = "_static/logo.svg"

html_css_files = [
    "css/custom.css",
]
html_context = {"default_mode": "light"}

html_theme_options = {
    "show_nav_level": 5,
    "github_url": "https://github.com/PedestrianDynamics/PedPy",
    "header_links_before_dropdown": 5,
    "show_toc_level": 5,
    "navbar_end": ["navbar-icon-links"],
}

# -- Options for EPUB output
epub_show_urls = "footnote"
