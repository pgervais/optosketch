"""Format links from text file to the Optosketch wiki.

See: http://gitorious.org/optosketch/pages/Bibliography

Use:

    $ python format2wiki.py > /tmp/wiki-biblio.txt

Then copy the contents of wiki-biblio.txt to the wiki edit area.
"""

def main(links_fname):
    """Format links found in text file"""
    title = None
    link_pattern = '* [%s](%s)'
    fid = open(links_fname)
    for line in fid:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'): # a header
            print
            print line
        elif (title is None):
            title = line
        else:
            print link_pattern % (title, line)
            title = None
    fid.close()


if __name__ == '__main__':
    main('biblio-links.txt')
