"""
    This module provides functionality to automatically override some or all
    of a classes function calls to replace them with a python script that will
    perform the calls later.

    There are three ways you can run this module:
        delayed
            Class function are only called after the save.
        concurrently
            Class functions are called immediately
        script only
            Class functions are only recorded

    If the program requires return values from the class functions then
    obviously functions would have to be called immediately.  This could
    still be used for version testing or debugging.
    
    Example:
        obj = my_class                      # creates my object like normal
        import proxy_script                 # import this module
        proxy_script.setup(obj)             # override my objects function calls
        obj.func1()                         # call my functions, but it log instead of execute
        obj.func2(1,[],'',{})               # ...
        proxy_script.save(obj,'my_file.py') # save python script file to execut funciton calls
        
    Written:
        Ben Christenson 
"""
    
import sys,os

def setup(self, do_script = None, dont_script = None, concurrent=False):
    """ This will replace each class subroutine with a logging mechanism
        that will simply store the function calls in self.script_data
            do_script
                This is a list of the object's functions to override, if
                not set it will be set to all functions.
            dont_script
                This is a list of the object's functions not to override.
            concurrent
                This will execute the class functions currently while scripting
        """
    import inspect
    self.script_data = []
    self.script_var = {}
    if do_script == None or do_script == []:
        do_script = dir(self)
        
    if dont_script != None:
        dont_script = []
        for f in dir(self):
            if(f.startswith('_')): dont_script.append(f)
    for func in dont_script:
        if(func in do_script): do_script.remove(func)
    
    for f in dir(self):
        func = eval('self.'+f)
        var_type = str(type(func))
        if(f in ['script_data','script_var']): pass
        elif(var_type in ["<type 'str'>","<type 'float'>","<type 'int'>","<type 'tuple'>","<type 'list'>","type 'dic'>"]):
            self.script_var[f] = pickle(func)
        elif(var_type == "<type 'instancemethod'>" and f in do_script):
            exec('self.original_'+f+' = self.'+f)
            temp = "def temp_func("
            args = inspect.getargspec(func)[0]
            arg_list = str(args[1:])
            defaults = func.func_defaults
            if(defaults != None):
                for i in range(-1*len(defaults),0):
                    if(type(defaults[i]) == type('')):
                        args[i] += '= "'+defaults[i]+'"'
                    else:
                        args[i] += '= '+str(defaults[i])
                # end for
            # end if
            args = str(args)[1:-1].replace("'","")
            temp = "def temp_func("+args+"): \n    script_func(self,'"+f+"',"+arg_list+","+arg_list.replace("'","")+")"
            if(concurrent):
                temp += '\n    return self.original_'+f+'('+arg_list.replace("'","")[1:-1]+')'
            exec(temp)
            setattr(self.__class__,f,temp_func)
        # end if
        setattr(self.__class__,'proxy_script_save',save)
    # end for
    setattr(self.__class__,'script_func',script_func)
    
def pickle(var):
    if(str(type(var)) == "<type 'str'>"):
        if('"' in var): return '"'+var+'"'
        else:           return "'"+var+"'"
    else:               return str(var)        
        
def script_func(self,function,arg_names,arg_values):
    """ When in script mode this function will be called instead of the class functions """
    source = ''
    for frame in range(2,6):
        f = sys._getframe(frame).f_code.co_name
        if(f == 'temp_func'): return # this is an internal call
        if(f == '?'): f = 'main'
        source = f+'.'+source
        if(f == 'main'): break
    self.script_data.append([source[:-1],function,arg_names,arg_values])
    
def save(self,file,execute = False,imports="",width = 30, tab = '    '):
    """ This will save the script as a python file, that once executed will
        call the classes functions as originally scripted.
        
        Args:
            file    # is the name of the file to save the python script as.
            execute # if set to True will then execute the python script
            imports # represnts a python code string of imports to use
            width   # represents the column within the documentation
            tab     # represents the length of the tab to use in the documentation
    
        If there is an error and the class has the function proxy_error then the
        python script will call that error handling routine with the following arguments:
            msg     # this is a short message of the function and arguments used
            i       # the line number in the documentation that failed
            cmd     # the actual command that failed to execute
            original_vars   # dictionary of the obj variables after initialization
            error_vars      # dictionary of the obj variables after exception

        See example at the bottom for an example of proxy_error """
    _class = self.__class__.__name__
    last_source = ''
    last_func = ''
    deliminator = ','
    doc = ['"""\n']
    max = 0
    for s in self.script_data:
        if(len(s[1]) > max): max = len(s[1])
    col = len(tab)*2+max+5
    
    for i in xrange(len(self.script_data)):
        s = self.script_data[i]
        if(last_source != s[0]):
            doc.append('\n'+tab+s[0])
            last_source = s[0]
            last_func = ''
        if(last_func != s[1]):
            doc.append('\n'+(tab*2+s[1]+'(').ljust(col))
            for a in s[2]:
                doc[-1] += (a+deliminator).ljust(width)
            if(s[2] == []):
                doc[-1] = doc[-1].rstrip()+')'
            else:
                doc[-1] = doc[-1].rstrip()[:-1]+')'
            last_func = s[1]
        doc.append(' '*col)
        for a in s[3]:
            if(type(a) == type('')):
                assert(not '"""' in a)
                if('\n' in a):
                    doc[-1] += '>"">\n\n'+a+'\n'+' '*col+'<""<,'.ljust(width)                    
                elif('"' in a): doc[-1] += ("'"+a+"'"+deliminator).ljust(width)
                else:         doc[-1] += ('"'+a+'"'+deliminator).ljust(width)
            else:
                doc[-1] += (str(a)+deliminator).ljust(width)
        # end for
        doc[-1] = doc[-1].rstrip()[:-1]
    # end for
    doc.append('\n\n"""\n\n')
    
    if(imports == ""):
        path,module = os.path.split(sys._getframe(2).f_code.co_filename.split('.')[0])
        if(path == ''): path = os.getcwd()
        path = path.replace('\\','\\\\')
        imports = ("""
                   import sys
                   sys.path.append('"""+path+"""')
                   from """+module+""" import *""").replace('\n                   ','\n')

    obj_init = '\n\n'+'obj = '+_class+'()'
    exec(imports+obj_init)
    keys = self.script_var.keys()
    keys.sort()
    obj_dir = dir(obj)
    for k in keys:
        try:
            if(not k in obj_dir):
                obj_init+= '\nobj.'+k+' = '+self.script_var[k]
            else:
                var = eval('obj.'+k)
                if(str(type(var)) in ["<type 'str'>","<type 'float'>","<type 'int'>","<type 'tuple'>","<type 'list'>","type 'dic'>"]):
                    var = pickle(var)
                    if(var != self.script_var[k]):
                        obj_init+= '\nobj.'+k+' = '+self.script_var[k]
            # end if
        except: print "Failed to set "+k
    # end for

    text = ("""
        def main():
            i = 0
            script = __doc__.strip().split('\\n')
            col = """+str(col)+"""
            while (i < len(script)):
                s = script[i]
                if('>"">' in s):
                    for j in range(1,len(script)-i):
                        if('<""<' in script[j+i] and not '>"">' in script[j+i]): break
                    s += '\\n' + '\\n'.join(script[i+1:j+i+1])
                    s = s.replace('>"">\\n\\n','<""<').replace('<""<','"""+'"""'+"""')
                else: j = 0
                
                cmd = ''
                if(s == ''): pass
                elif(s.startswith('"""+tab*3+"""')):
                    cmd = 'obj.'+func+'('+s[col:]+')'
                elif(s.startswith('"""+tab*2+"""')):
                    func = s.split('(',1)[0].strip()
                    if(s.strip() == func+'()'): cmd = 'obj.'+func+'()'
                else:
                    source = s.strip()
                    func = ''
                    print str(i).rjust(7)+':: Processing '+source
                # end if
                
                try:
                    if(cmd): exec(cmd)
                except:
                    if(len(cmd) > 80): msg = 'Error Processing CMD '+str(i)+' :: '+cmd[:80]+'...'
                    else:              msg = 'Error Processing CMD '+str(i)+' :: '+cmd
                    if('script_error' in dir(obj)):
                        error_vars = obj_vars(obj)
                        obj.script_error(msg,i,cmd,original_vars,error_vars)
                    else:
                        print '\\n\\n'+msg
                    return
                i += j + 1
            # end while                                
                        
        def pickle(var):
            if(str(type(var)) == "<type 'str'>"):
                if('"' in var): return '"'+var+'"'
                else:           return "'"+var+"'"
            else:               return str(var)        

        def obj_vars(obj):
            ret = {}
            for k in dir(obj):
                var = eval('obj.'+k)
                if(str(type(var)) in ["<type 'str'>","<type 'float'>","<type 'int'>","<type 'tuple'>","<type 'list'>","type 'dic'>"]):
                    ret[k] = pickle(var)
            return ret

        original_vars = obj_vars(obj)
        if(__name__ == '__main__'): main()   """).replace('\n        ','\n')
    if(file[-3:] != '.py'): file = file.split('.')[0]+'.py'
    fn = open(file,'w')
    fn.write('\n'.join(doc)+imports+obj_init+text)
    fn.close()
    self.script_data = []
    if(execute):        
        print os.popen('python.exe '+file).read()
# end def

#############################################################
##              TEST ROUTINES AFTER THIS POINT             ##
#############################################################
        
class test_script:
    def __init__(self): self.name = 'test'
    def dont_test(self,arg1,arg2=None):
        print '             dont_test('+str(arg1)+','+str(arg2)+')'
    def test1(self,arg1=None):
        print '             test1('+str(arg1)+')'
    def test2(self,arg1=None,arg2=2):
        print '             test2('+str(arg1)+','+str(arg2)+')'
    def test3(self,arg1=None,arg2=2,arg3=[]):
        print '             test3('+str(arg1)+','+str(arg2)+','+str(arg3)+')'
    def test4(self,arg1,arg2={},arg3="hello,world",arg4=None):
        print '             test4('+str(arg1)+','+str(arg2)+','+str(arg3)+','+str(arg4)+')'        

    def script_error(self,msg,i,cmd,original_vars,error_vars):
        """ This will be called if the controller proxy script throws an exception
            It will attempt to make a new proxy script starting right before the error "
            
            This example was from a different project so the internal functions aren't present,
            but hopefully you get the idea."""
        try:
            error(msg = msg)
            file = sys._getframe(1).f_code.co_filename[:-3]
            text = read(file+'.py')
            new_startup = "def main():\n"
            new_startup+= "    i = "+str(i)+"\n"
            new_startup+= "    obj.open_excel('"+file+"_error.xlsb')\n"
            keys = error_vars.keys()
            keys.sort()
            for k in keys:
                if(not original_vars.has_key(k) or error_vars[k] != original_vars[k]):
                    new_startup += '    obj.'+k+' = '+error_vars[k]+'\n'
            text = text.replace('def main():\n    i = 0',new_startup)
            save(file+'_error.py',text)
            self.save_and_close(file+'_error.xlsb')
        except: error()            
        
def main():
    """ This will create a test routine call proxy_script_test.py """
    import proxy_controller
    t = test_script()
    proxy_controller.setup(t,do_script=None,dont_script = ['dont_test'],concurrent=False)

    def source_test(t):
        print 'calling test1'
        t.test1()
        print 'calling test2(2,3)'
        t.test2()
        print 'calling test3(None,hello,'+str(range(5))+')'
        t.test3(None,'hello',range(5))
        print "calling test4({'hello':'cruel, \\n World'},"+str(range(5))+",None,1)"
        t.test4({'hello':'cruel, \\n World'},range(5),None,1)
    
    print('calling test1')
    t.test1()
    print('calling test2')
    t.test2()
    print('calling test2(1,2)')
    t.test2(1,2)
    source_test(t)
    proxy_controller.save(t,'proxy_controller_test',True)

if(__name__ == '__main__'): main()

