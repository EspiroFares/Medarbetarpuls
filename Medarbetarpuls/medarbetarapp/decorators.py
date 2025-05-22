from functools import wraps
from django.shortcuts import redirect

#possible roles: surveyresponder, surveycreator, admin
def allowed_roles(*allowed_roles):
    """
        Decorator function that checks if the user
        is in the allowed roles for that page 

        Args:
            The allowed roles for that page

        Returns:
            Redirects to specific roles start page if not in allowed role otherwise nothing
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check if user is in the allowed roles for this page
            if request.user.user_role not in allowed_roles:
                # If not in allowed roles redirect to specific roles start page
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
    """ 
        Decorator function that checks if the user
        is logged in then it redirects to correct start page 

        Args:
            Nothing

        Returns:
            Redirects to specific roles start page if logged in otherwise nothing
    """     
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check if user is logged in
            if request.user.is_authenticated:
                # Redirect to specific roles start page
                if(request.user.user_role == 'admin'):
                    return redirect('/start-admin/')
                elif(request.user.user_role == 'surveycreator'):
                    return redirect('/start-creator/')
                else:
                    return redirect('/start-user/')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


    
