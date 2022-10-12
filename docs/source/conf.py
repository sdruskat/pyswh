# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'pyswh'
copyright = '2022, Stephan Druskat'
author = 'Stephan Druskat'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.intersphinx',
    'autoapi.extension',
    'myst_parser'
]

templates_path = ['_templates']
exclude_patterns = []

# Autoapi package config
autoapi_dirs = ['../../src/pyswh']
autoapi_type = 'python'
autoapi_options = [
    'members',
    'undoc-members',
    'show-inheritance',
    'show-module-summary',
    'imported-members',
    # 'show-inheritance-diagram'
]
autoapi_add_toctree_entry = False

# Intersphinx config
intersphinx_mapping = {
    'requests': ('https://requests.readthedocs.io/en/latest/', None),
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
