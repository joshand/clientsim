from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponseRedirect
from django.shortcuts import render
from .forms import UploadFileForm
from .models import *


def show_home(request):
    return render(request, 'home.html')


def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # instance = Upload(file=request.FILES['file'].file.read(), description=request.FILES['file'])
            # instance.save()
            form.save()
            return HttpResponseRedirect('/upload/')
    else:
        form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})


def show_log(request):
    cli_parm = request.GET.get("cli")
    cli = Client.objects.filter(id=cli_parm)
    if cli:
        clientid = cli[0].clientid
        client = docker.from_env()
        dlogs = client.containers.get(clientid).logs(until=120)
    else:
        dlogs = None
    return render(request, 'logs.html', {'logs': dlogs})