from urlparse import urljoin

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from silo.models import HikayaUser
from silo.serializers import TolaUserSerializer
from hikaya.forms import (RegistrationForm, NewUserRegistrationForm,
                          NewTolaUserRegistrationForm)

from rest_framework_swagger.renderers import OpenAPIRenderer, SwaggerUIRenderer
from rest_framework.decorators import api_view, renderer_classes
from rest_framework import response, schemas
from rest_framework.response import Response
from rest_framework import status


@api_view()
@renderer_classes([OpenAPIRenderer, SwaggerUIRenderer])
def schema_view(request):
    generator = schemas.SchemaGenerator(title='Assets API')
    return response.Response(generator.get_schema(request=request))


@api_view(['POST'])
def register(request):
    """
    Register a new User profile using built in Django Users Model
    """
    if request.user.is_superuser:
        form_user = NewUserRegistrationForm(request.POST)
        form_hikayauser = NewTolaUserRegistrationForm(request.POST)

        if form_user.is_valid() and form_hikayauser.is_valid() and \
                request.POST.get('hikaya_user_uuid'):
            user = form_user.save()

            hikayauser = form_hikayauser.save(commit=False)
            hikayauser.user = user
            hikayauser.organization = form_hikayauser.cleaned_data.get('org')
            hikayauser.name = ' '.join([user.first_name, user.last_name]).strip()
            hikayauser.hikaya_user_uuid = request.POST.get('hikaya_user_uuid')
            hikayauser.save()
            serializer = TolaUserSerializer(
                hikayauser, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    return Response(status=status.HTTP_403_FORBIDDEN)


def profile(request):
    """
    Update a User profile using built in Django Users Model if the user
    is logged in otherwise redirect them to registration version
    """
    if request.user.is_authenticated:
        obj = get_object_or_404(HikayaUser, user=request.user)
        form = RegistrationForm(request.POST or None, instance=obj,
                                initial={'username': request.user})

        if request.method == 'POST':
            if form.is_valid():
                form.save()
                messages.error(request,
                               'Your profile has been updated.',
                               fail_silently=False)

        return render(request, "registration/profile.html", {
            'form': form, 'helper': RegistrationForm.helper
        })
    else:
        return HttpResponseRedirect("/accounts/register")


def logout_view(request):
    """
    Logout a user in activity and track
    """
    # Redirect to activity, so the user will
    # be logged out there as well
    if request.user.is_authenticated:
        logout(request)
        return HttpResponseRedirect('/accounts/login')

    return HttpResponseRedirect(settings.ACTIVITY_URL)


class BoardView(LoginRequiredMixin, TemplateView):
    template_name = 'board.html'

    def render_to_response(self, context, **response_kwargs):
        response = super(BoardView, self).render_to_response(
            context, **response_kwargs)
        if self.request.user.is_authenticated:
            response.set_cookie(key='token',
                                value=self.request.user.auth_token)
        return response


def user_login(request):
    if request.method == 'POST':
        data = request.POST
        username = data.get('username')
        password = data.get('password')

        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            return HttpResponseRedirect('/')

        else:
            render(request, 'registration/login.html')
    return render(request, 'registration/login.html')
