from functools import wraps
from django.shortcuts import redirect

#possible roles: surveyresponder, surveycreator, admin
def allowed_roles(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        # the args are to fit in with any view undepending on 
        # what type and how many args that view takes
        def _wrapped_view(request, *args, **kwargs):
            if request.user.user_role not in allowed_roles:
                if(request.user.user_role == 'admin'):
                    return redirect('/start-admin/')
                elif(request.user.user_role == 'surveycreator'):
                    return redirect('/start-creator/')
                else:
                    return redirect('/start-user/')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def logout_required():
    def decorator(view_func):
        @wraps(view_func)
        # the args are to fit in with any view undepending on 
        # what type and how many args that view takes
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                if(request.user.user_role == 'admin'):
                    return redirect('/start-admin/')
                elif(request.user.user_role == 'surveycreator'):
                    return redirect('/start-creator/')
                else:
                    return redirect('/start-user/')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


    
