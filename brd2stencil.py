import math
import xml.etree.ElementTree as ET
from optparse import OptionParser

svg_prefix = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:cc="http://creativecommons.org/ns#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   width="210mm"
   height="297mm"
   viewBox="0 0 744.09448819 1052.3622047"
   id="svg4154"
   version="1.1"
   inkscape:version="0.91 r13725"
   sodipodi:docname="blank.svg">
  <defs
     id="defs4156" />
  <sodipodi:namedview
     id="base"
     pagecolor="#ffffff"
     bordercolor="#666666"
     borderopacity="1.0"
     inkscape:pageopacity="0.0"
     inkscape:pageshadow="2"
     inkscape:zoom="0.35"
     inkscape:cx="-467.86"
     inkscape:cy="405.71"
     inkscape:document-units="px"
     inkscape:current-layer="layer1"
     showgrid="false"
     inkscape:window-width="1920"
     inkscape:window-height="1017"
     inkscape:window-x="-8"
     inkscape:window-y="-8"
     inkscape:window-maximized="1" />
  <metadata
     id="metadata4159">
    <rdf:RDF>
      <cc:Work
         rdf:about="">
        <dc:format>image/svg+xml</dc:format>
        <dc:type
           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />
        <dc:title />
      </cc:Work>
    </rdf:RDF>
  </metadata>
  <g
     inkscape:label="Layer 1"
     inkscape:groupmode="layer"
     id="layer1">
"""

svg_suffix = "  </g>\n</svg>"

def brd_to_svg(boardpath, layer, PIXELS_PER_MM, PAD_SHRINK_MM):
    if boardpath[-4:].lower() != ".brd": raise SystemExit("File must be a .BRD file")
    print "\nProcessing " + layer + " layer of BRD file " + boardpath + "..."
    layercode = 1
    if layer == "bottom": layercode = 16
    try:
        #PARSE BRD AS XML TREE
        tree = ET.parse(boardpath)
        root = tree.getroot()

        #BUILD DICT OF SMD PADS, BY LIBRARY AND PACKAGE NAMES
        smd_dict = {}
        for lib in root.findall('./drawing/board/libraries/library'):
            libname = lib.get("name")
            for pkg in lib.findall('./packages/package'):
                pkgname = pkg.get('name')
                smds = pkg.findall('smd')
                if len(smds) > 0:
                    if libname not in smd_dict: smd_dict[libname] = {}
                    if pkgname not in smd_dict[libname]: smd_dict[libname][pkgname] = {}
                    for smd in smds:
                        (srot, smir, sspin) = parse_rot(smd.get('rot'))
                        smd_dict[libname][pkgname][smd.get('name')] = {"name":smd.get('name'), "x":float(smd.get('x')), "y":float(smd.get('y')), "dx":float(smd.get('dx')), "dy":float(smd.get('dy')), "rot":float(srot), "layer":int(smd.get('layer'))}
                        pad = smd_dict[libname][pkgname][smd.get('name')]
                        
        #FIND ALL ELEMENTS MATCHING SMD DICT ON LIBRARY AND PACKAGE NAMES
        pads_dict = {}                
        svg_bbox = [[0,0],[0,0]]
        for elem in root.findall('./drawing/board/elements/element'):
            elib = elem.get('library')
            epkg = elem.get('package')
            ename = elem.get('name')
            if(elib in smd_dict):
                if(epkg in smd_dict[elib]):
                    ex = float(elem.get('x'))
                    ey = float(elem.get('y'))
                    (erot, emir, espin) = parse_rot(elem.get('rot'))
                    erot = float(erot) * math.pi/180.0
                    for smd in smd_dict[elib][epkg]:
                        smd_layer = 1 #presume layer = 1, emir = 0
                        pad = smd_dict[elib][epkg][smd]
                        if pad['layer'] == 1 and emir == 1: smd_layer = 16
                        elif pad['layer'] == 16 and emir == 0: smd_layer = 16
                        elif pad['layer'] == 16 and emir == 1: smd_layer = 1
                        if smd_layer == layercode:
                            px = float(pad['x'])
                            py = float(pad['y'])
                            dx = float(pad['dx']) - 2.0 * PAD_SHRINK_MM
                            dy = float(pad['dy']) - 2.0 * PAD_SHRINK_MM
                            rot = pad['rot'] * math.pi / 180.0
                            hx = dx/2.0 
                            hy = dy/2.0
                            coords = [[hx,hy],[hx-dx,hy],[hx-dx,hy-dy],[hx,hy-dy]]
                            for c in coords:
                                cx = c[0] * math.cos(rot) - c[1] * math.sin(rot)
                                cy = c[0] * math.sin(rot) + c[1] * math.cos(rot)
                                #Position of pads in package in library, with package centroid at origin:
                                c[0] = cx + px
                                c[1] = cy + py
                            #Now rotate each point in coords by the element's rotation, and offset resulting coords by the element centroid
                            padsname = ename + "_" + pad['name']
                            for c in coords:
                                cx = c[0] * math.cos(erot) - c[1] * math.sin(erot)
                                cy = c[0] * math.sin(erot) + c[1] * math.cos(erot)
                                c[0] = cx + ex
                                c[1] = cy + ey
                                #convert mm to pixels and get full bounding box
                                pix_x = c[0] * PIXELS_PER_MM
                                pix_y = c[1] * PIXELS_PER_MM
                                if pix_x < svg_bbox[0][0]: svg_bbox[0][0] = pix_x
                                if pix_y < svg_bbox[0][1]: svg_bbox[0][1] = pix_y
                                if pix_x > svg_bbox[1][0]: svg_bbox[1][0] = pix_x
                                if pix_y > svg_bbox[1][1]: svg_bbox[1][1] = pix_y
                            #Correctly placed points for each pad of each element on the board, in pixels
                            pads_dict[padsname] = coords
        svg_infix = ""
        for k,v in pads_dict.iteritems():
            #build SVG polygon element tags, inverting y coordinates to match SVG coordinate system
            coords_string = ""
            for c in v:
                coords_string += str(c[0] * PIXELS_PER_MM) + "," + str(svg_bbox[1][1] - c[1] * PIXELS_PER_MM) + " "
            svg_infix += "<polygon points=\"" + coords_string[:-1] + "\" style=\"fill:black;stroke:black;stroke-width:0\" />\n"
        svg_text = svg_prefix + svg_infix + svg_suffix
        svg_out = open(boardpath[:-4] + "_" + layer + ".svg", "w")
        svg_out.write(svg_text)
        svg_out.close()
        print "DONE"
    except Exception as e: print str(e)

def parse_rot(rotstr):
    rot = 0
    mir = 0
    spin = 0
    if rotstr != None:
        if "M" in rotstr: mir = 1
        if "S" in rotstr: spin = 1
        rot = ''.join(c for c in rotstr if c.isdigit())
    return (rot, mir, spin)

def main():
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="file", help="make svg of pads from BRD", metavar="BRD")
    parser.add_option("-F", "--folder", dest="folder", help="make svg of pads from folder of BRDs", metavar="FLD")
    parser.add_option("-l", "--layer", dest="layer", help="t=top, b=bottom", default="t")
    parser.add_option("-p", "--pixels", action="store", type="int", dest="ppi", default=90, help="pixels per inch (90 or 96 for Inkscape)")
    parser.add_option("-s", "--shrink", action="store", type="float", dest="shr", default=2, help="mils to shrink pad mask by (default 2)")
    (options, args) = parser.parse_args()

    ppm = 3.543307 
    if options.ppi != None: ppm = float(options.ppi) / 25.4

    shrink = 0.0508
    if options.shr != None: shrink = float(options.shr) * 0.0254

    layer = "top"
    if options.layer == "b": layer = "bottom"
    
    f = options.file
    F = options.folder

    if f == None and F == None:  raise SystemExit("\n*You must specify a folder or a file...")
    elif f == None:  raise SystemExit("\nFolder operations are not yet supported...")
    elif F == None:  brd_to_svg(f, layer, ppm, shrink)
    else:
        print "\N* File and folder arguments detected. Defaulting to file..."
        brd_to_svg(f, layer, ppm, shrink)

if __name__ == '__main__':
  main()
