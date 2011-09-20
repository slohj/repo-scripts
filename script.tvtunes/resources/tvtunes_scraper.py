# -*- coding: utf-8 -*-
__useragent__    ="Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"
import urllib
import os
from traceback import print_exc
import re
import unicodedata
import xbmc  
import xbmcaddon
import xbmcgui
import xbmcvfs

__addon__     = xbmcaddon.Addon(id='script.tvtunes')
__addonid__   = __addon__.getAddonInfo('id')
__cwd__       = __addon__.getAddonInfo('path')
__language__  = __addon__.getLocalizedString

def log(msg):
    xbmc.log( str( msg ),level=xbmc.LOGDEBUG )

try:
    # parse sys.argv for params
    log( sys.argv[ 1 ] )
    try:params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
    except:
        print_exc()
        params = dict( sys.argv[ 1 ].split( "=" ))
except:
    # no params passed
    print_exc()
    params = {} 

def get_html_source( url , save=False):
    """ fetch the html source """
    class AppURLopener(urllib.FancyURLopener):
        version = __useragent__
    urllib._urlopener = AppURLopener()

    try:
        if os.path.isfile( url ): sock = open( url, "r" )
        else:
            urllib.urlcleanup()
            sock = urllib.urlopen( url )

        htmlsource = sock.read()
        if save: file( os.path.join( CACHE_PATH , save ) , "w" ).write( htmlsource )
        sock.close()
        return htmlsource
    except:
        print_exc()
        log( "### ERROR opening page %s" % url )
        xbmcgui.Dialog().ok(__language__(32101) , __language__(32102))
        return False

class TvTunes:
    def __init__(self):
        if not xbmcvfs.exists( xbmc.translatePath( 'special://profile/addon_data/%s/temp' % __addonid__ ) ):
            os.makedirs( xbmc.translatePath( 'special://profile/addon_data/%s/temp' % __addonid__ ) )
        self.search_url = "http://www.televisiontunes.com/search.php?searWords=%s&Send=Search"
        self.download_url = "http://www.televisiontunes.com/download.php?f=%s"
        self.theme_file = "theme.mp3"
        self.TVlist = self.listing()
        self.DIALOG_PROGRESS = xbmcgui.DialogProgress()
        self.ERASE = xbmcgui.Dialog().yesno(__language__(32103),__language__(32104))
        self.DIALOG_PROGRESS.create( __language__(32105) , __language__(32106) )
        if params.get("mode", "false" ) == "solo" : self.scan(params.get("name", "" ),params.get("path", "false" ))
        else: self.scan()

    def scan(self , cur_name=False , cur_path=False):
        count = 0
        if cur_name and cur_path: 
            log( "solo mode" )
            self.TVlist = [[cur_name,cur_path.encode('utf-8')]]
        total = len(self.TVlist)
        for show in self.TVlist:
            count = count + 1
            if not self.ERASE and xbmcvfs.exists(os.path.join(show[1],"theme.mp3")):
                log( "### %s already exists, ERASE is set to %s" % (os.path.join(show[1],"theme.mp3"), [False,True][self.ERASE] ) )
            else:
                self.DIALOG_PROGRESS.update( (count*100)/total , __language__(32107) + ' ' + show[0] , "")
                if self.DIALOG_PROGRESS.iscanceled():
                    self.DIALOG_PROGRESS.close()
                    xbmcgui.Dialog().ok(__language__(32108),__language__(32109))
                    break
                theme_list = self.search_theme_list( show[0])
                #log( theme_list )
                if len(theme_list) == 1: theme_url = self.download_url % theme_list[0]["url"].replace("http://www.televisiontunes.com/", "").replace(".html" , "")
                else: theme_url = self.get_user_choice( theme_list , show[0] )
                if theme_url: self.download(theme_url , show[1])

    def download(self , theme_url , path):
        log( "### download :" + theme_url )
        tmpdestination = xbmc.translatePath( 'special://profile/addon_data/%s/temp/%s' % ( __addonid__ , self.theme_file ) )
        destination = os.path.join( path , self.theme_file)
        try:
            def _report_hook( count, blocksize, totalsize ):
                percent = int( float( count * blocksize * 100 ) / totalsize )
                strProgressBar = str( percent )
                self.DIALOG_PROGRESS.update( percent , __language__(32110) + ' ' + theme_url , __language__(32111) + ' ' + destination )
            if xbmcvfs.exists(path):
                fp , h = urllib.urlretrieve( theme_url , tmpdestination , _report_hook )
                log( h )
                copy = xbmcvfs.copy(tmpdestination, destination)
                if copy:
                    log( "### copy successful" )
                else:
                    log( "### copy failed" )
                xbmcvfs.delete(tmpdestination)
                return True
            else : log( "problem with path: %s" % destination )
        except :
            log( "### Theme download Failed !!!" )
            print_exc()
            return False 

    def get_user_choice(self , theme_list , showname):
        #### on cree la liste de choix de theme
        theme_url = False
        searchname = showname
        searchdic = { "name" : "Manual Search..."}
        theme_list.insert(0 , searchdic)
        while theme_url == False:

            select = xbmcgui.Dialog().select(__language__(32112) + ' ' + searchname, [ theme["name"] for theme in theme_list ])
            if select == -1: 
                log( "### Canceled by user" )
                #xbmcgui.Dialog().ok("Canceled" , "Download canceled by user" )
                return False
            else:
                if theme_list[select]["name"] == "Manual Search...":
                    kb = xbmc.Keyboard(showname, __language__(32113), False)
                    kb.doModal()
                    result = kb.getText()
                    theme_list = self.search_theme_list(result)
                    searchname = result
                    theme_list.insert(0 , searchdic)
                else:
                    theme_url = self.download_url % theme_list[select]["url"].replace("http://www.televisiontunes.com/", "").replace(".html" , "")
                    log( "### %s" % theme_url )
                    listitem = xbmcgui.ListItem(theme_list[select]["name"])
                    listitem.setInfo('music', {'Title': theme_list[select]["name"]})
                    xbmcgui.Window( 10025 ).setProperty( "TvTunesIsAlive", "true" )
                    xbmc.Player().play(theme_url, listitem)
                    ok = xbmcgui.Dialog().yesno(__language__(32103),__language__(32114))
                    if not ok: theme_url = False
                    xbmc.executebuiltin('PlayerControl(Stop)')
                    xbmcgui.Window( 10025 ).clearProperty('TvTunesIsAlive')

        return theme_url

    def search_theme_list(self , showname):
        log( "### Search for %s" % showname )
        ### on nettoie le nom des caract pas cool (type ": , ; , ...")
        showname = showname.replace(":","")
        theme_list = []
        next = True
        url = self.search_url % urllib.quote_plus(showname)
        urlpage = ""
        while next == True:
            ### on recup le result de la recherche
            data = get_html_source( url + urlpage )
            log( "### Search url: %s" % ( url + urlpage ) )
            ###on parse la recherche pour renvoyer une liste de dico
            match = re.search(r"1\.&nbsp;(.*)<br>", data)
            if match: data2 = re.findall('<a href="(.*?)">(.*?)</a>', match.group(1))
            else: 
                log( "no theme found for %s" % showname )
                data2 = ""
            for i in data2:
                theme = {}
                theme["url"] = i[0] or ""
                theme["name"] = i[1] or ""
                theme_list.append(theme)
            match = re.search(r'&search=Search(&page=\d)"><b>Next</b>', data)
            if match:
            	urlpage = match.group(1)
            else:
            	next = False
            log( "### next page: %s" % next )
        return theme_list

    def listing(self):
        # on recup la liste des series en biblio
        # json statement for tv shows
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file"], "sort": { "method": "label" } }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        log( json_response )
        TVlist = []
        for tvshowitem in json_response:
            log( tvshowitem )
            findtvshowname = re.search( '"label": ?"(.*?)",["\n]', tvshowitem )
            if findtvshowname:
                tvshowname = ( findtvshowname.group(1) )
                tvshow = unicodedata.normalize('NFKD', unicode(unicode(tvshowname, 'utf-8'))).encode('ascii','ignore')
                findpath = re.search( '"file": ?"(.*?)",["\n]', tvshowitem )
                if findpath:
                    path = (findpath.group(1))
                    TVlist.append( ( tvshow , path ) )
        return TVlist   
              
if ( __name__ == "__main__" ):
    TvTunes()
    xbmcgui.Dialog().ok(__language__(32115),__language__(32116) , __language__(32117))
# fp , h = urllib.urlretrieve("http://www.televisiontunes.com/download.php?f=Alias 1".replace(" " , "_" ) , os.path.join(__cwd__ , "theme.mp3"))
# log( fp,h )


