#!/usr/bin/env python
import sys, logging
from functools import wraps
import types

def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.
    
    If strings_only is True, don't convert (some) non-string-like objects.

    (modified from django.util.encoding)
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    elif not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s

def _get_lines_from_file(filename, lineno, context_lines):
    """
    Returns context_lines before and after lineno from file.
    Returns (pre_context_lineno, pre_context, context_line, post_context).
    """
    try:
        source = open(filename).readlines()
        lower_bound = max(0, lineno - context_lines)
        upper_bound = lineno + context_lines

        pre_context = [line.strip('\n') for line in source[lower_bound:lineno]]
        context_line = source[lineno].strip('\n')
        post_context = [line.strip('\n') for line in source[lineno+1:upper_bound]]

        return lower_bound, pre_context, context_line, post_context
    except (OSError, IOError):
        return None, [], None, []

def add_newline_dec(f):
    def decorator(string):
        return f(string + '\n')
    return decorator

def log_exception(write_func = logging.error, add_newline = False):
    """ log traceback information in a readable way
        write_func - a function used to write exceptions, receieves string
        add_newline - if True, adds a newline to every line passed to write_func

        Magic Variables:

        If you define one of these variables in your local scope, you can add information 
        to tracebacks that happen in that context. This allows applications to add all sorts
        of extra information about the context of the error

        ``__traceback_hide__``:
            If set and true, this indicates that the frame should be hidden from abbreviated tracebacks.
            (the frame won't be logged) This allows to hide some of the complexety of the traceback and
            let the user focus on the relevant path

        ``__traceback_hide_all_vars__``:
            If set and true, this indicates that all the vars in this context should be hidden (in order to avoid 
            leak of information)

        ``__traceback_hide_vars__``:
            [variable which supports "in"] if set, variable names in __traceback_hide_vars__ aren't logged.
        
        ``__traceback_expand_vars__``:
            [variable which supports "in"] if set, variable names in __traceback_expand_vars__ are expanded (otherwise, only the first 40 chars are displayed).
        
        ``__traceback_stop__``:
            If set and true, stop traversing traceback in lower levels
        
        ``__traceback_stop_display_vars__``:
            If set and true, stop traversing displaying variables in lower levels
        
        ``__traceback_start__``:
            If set and true, start up the traceback again, if ``__traceback_stop__`` has come into play
        
        ``__traceback_start_display_vars__``:
            If set and true, start up displaying variables again, if ``__traceback_stop_display_vars__`` has come into play

    """
    if add_newline:
        write_func = add_newline_dec(write_func)
    exc_type, exc_value, tb = sys.exc_info()
    traceback_stop = False
    traceback_stop_display_vars = False
    while tb is not None:
        # control tracback options
        if tb.tb_frame.f_locals.get('__traceback_stop__', False):
            traceback_stop = True
        if tb.tb_frame.f_locals.get('__traceback_start__', False):
            traceback_stop = False
        if tb.tb_frame.f_locals.get('__traceback_stop_display_vars__', False):
            traceback_stop_display_vars = True
        if tb.tb_frame.f_locals.get('__traceback_start_display_vars__', False):
            traceback_stop_display_vars = False
        
        # skip frame if traceback_stop is set to True, or __traceback_hide__ is set in local context
        if traceback_stop or tb.tb_frame.f_locals.get('__traceback_hide__'):
            tb = tb.tb_next
            continue

        filename = tb.tb_frame.f_code.co_filename
        #function = tb.tb_frame.f_code.co_name
        lineno = tb.tb_lineno - 1
        pre_context_lineno, pre_context, context_line, post_context = _get_lines_from_file(filename, lineno, 4)
        if pre_context_lineno:
            write_func('File: %r, line number: %s' % (filename, lineno+1))
            for line in pre_context:
                write_func('    %s' % line)
            write_func('--> %s' % context_line)
            for line in post_context:
                write_func('    %s' % line)
            write_func('%s: %s' % (exc_type.__name__, exc_value))
            vars = tb.tb_frame.f_locals
            write_func('%-20s %-10s %-58s' % ('Variable','Type','Value'))
            write_func('%-20s %-10s %-58s' % ('--------','----','-----'))
            # if __traceback_hide_all_vars__ is set in context, or traceback_stop_display_vars is set to True, don't display any variables 
            if vars.get('__traceback_hide_all_vars__') or traceback_stop_display_vars:
                write_func('        (variables are hidden)')
                write_func('')
                tb = tb.tb_next
                continue
            expand_vars = vars.get('__traceback_expand_vars__', [])
            hide_vars   = vars.get('__traceback_hide_vars__', [])
            for var in sorted(vars):
                if var.startswith('__traceback'):
                    continue
                v = vars[var]
                try:
                    s_v = smart_str(v)
                except:
                    s_v = '[error getting value]'
                if var in hide_vars:
                    write_func('%-20s %-10s %-58s' % (var, type(v).__name__, '[hidden]'))
                elif var in expand_vars:
                    write_func('%-20s %-10s %-58s' % (var, type(v).__name__, s_v))
                else:
                    write_func('%-20s %-10s %-58s' % (var, type(v).__name__, s_v[:40]))
            write_func('')
        tb = tb.tb_next

def log_except(write_func = logging.error, add_newline = False):
    def wrapper(func):
        @wraps(func)
        def logger(*args, **kwargs):
            __traceback_hide__ = True
            try:
                return func(*args, **kwargs)
            except:
                log_exception(write_func, add_newline)
                raise
        return logger
    return wrapper

