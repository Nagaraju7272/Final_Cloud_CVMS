import boto3
from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from datetime import datetime, timezone

# Initialize AWS services with debug
print(f"Loading AWS region: {settings.AWS_S3_REGION_NAME.strip() if settings.AWS_S3_REGION_NAME else 'Not set'}")
print(f"AWS_ACCESS_KEY_ID: {settings.AWS_ACCESS_KEY_ID if settings.AWS_ACCESS_KEY_ID else 'Not set'}")
print(f"AWS_SESSION_TOKEN: {settings.AWS_SESSION_TOKEN if settings.AWS_SESSION_TOKEN else 'Not set'}")
print(f"AWS_SECRET_ACCESS_KEY: {settings.AWS_SECRET_ACCESS_KEY[:4] if settings.AWS_SECRET_ACCESS_KEY else 'Not set'}... (partial for security)")
print(f"AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME if settings.AWS_STORAGE_BUCKET_NAME else 'Not set'}")
try:
    dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_S3_REGION_NAME.strip())
    s3 = boto3.client('s3', region_name=settings.AWS_S3_REGION_NAME.strip())
    sns = boto3.client('sns', region_name=settings.AWS_S3_REGION_NAME.strip())
    table = dynamodb.Table('Visitors')
    print("AWS clients initialized successfully")
except Exception as e:
    print(f"Error initializing AWS clients: {str(e)}")
    raise

@login_required
def dashboard(request):
    try:
        print("Attempting to scan DynamoDB table...")
        response = table.scan()
        visitors = response['Items']
        visitor_count = len(visitors)
        print(f"Successfully scanned {visitor_count} visitors")
    except Exception as e:
        print(f"Error scanning DynamoDB: {str(e)}")
        return HttpResponse(f"Error fetching dashboard data: {str(e)}", status=500)
    return render(request, 'dashboard.html', {'visitor_count': visitor_count})

@login_required
def visitors(request):
    try:
        print("Attempting to scan DynamoDB table...")
        response = table.scan()
        visitors = response['Items']
        print(f"Successfully scanned {len(visitors)} visitors")
    except Exception as e:
        print(f"Error scanning DynamoDB: {str(e)}")
        return HttpResponse(f"Error fetching visitors: {str(e)}", status=500)
    return render(request, 'visitors.html', {'visitors': visitors})

@login_required
def add_visitor(request):
    if request.method == 'POST':
        try:
            name = request.POST['name']
            phone = request.POST['phone']
            entry_time = datetime.now(timezone.utc).isoformat()
            photo = request.FILES.get('photo')

            if photo:
                s3.upload_fileobj(photo, settings.AWS_STORAGE_BUCKET_NAME, f'photos/{phone}_{photo.name}')
                photo_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/photos/{phone}_{photo.name}"
            else:
                photo_url = None

            print(f"Adding visitor: {name}, {phone}")
            table.put_item(
                Item={
                    'phone': phone,
                    'name': name,
                    'entry_time': entry_time,
                    'exit_time': None,
                    'photo_url': photo_url
                }
            )
            message = f"New visitor added: {name} (Phone: {phone}) at {entry_time}"
            sns.publish(TopicArn=settings.SNS_TOPIC_ARN, Message=message, Subject="New Visitor")
        except Exception as e:
            print(f"Error adding visitor: {str(e)}")
            return HttpResponse(f"Error adding visitor: {str(e)}", status=500)

        return redirect('visitors')
    return render(request, 'add_visitor.html')

@login_required
def update_visitor(request, phone):
    try:
        print(f"Fetching visitor with phone: {phone}")
        visitor = table.get_item(Key={'phone': phone})['Item']
    except Exception as e:
        print(f"Error fetching visitor: {str(e)}")
        return HttpResponse("Visitor not found or error occurred.", status=404)

    if request.method == 'POST':
        try:
            name = request.POST['name']
            new_phone = request.POST['phone']
            exit_time = request.POST.get('exit_time')
            photo = request.FILES.get('photo')

            print(f"Original phone (URL): {phone}, New phone (form): {new_phone}")

            if photo:
                s3.upload_fileobj(photo, settings.AWS_STORAGE_BUCKET_NAME, f'photos/{new_phone}_{photo.name}')
                photo_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/photos/{new_phone}_{photo.name}"
            else:
                photo_url = visitor.get('photo_url')

            table.update_item(
                Key={'phone': phone},
                UpdateExpression="SET #n = :n, exit_time = :e, photo_url = :pu",
                ExpressionAttributeNames={'#n': 'name'},
                ExpressionAttributeValues={
                    ':n': name,
                    ':e': exit_time if exit_time else None,
                    ':pu': photo_url
                }
            )

            if phone != new_phone:
                table.delete_item(Key={'phone': phone})
                table.put_item(
                    Item={
                        'phone': new_phone,
                        'name': name,
                        'entry_time': visitor['entry_time'],
                        'exit_time': exit_time if exit_time else None,
                        'photo_url': photo_url
                    }
                )
        except Exception as e:
            print(f"Error updating visitor: {str(e)}")
            return HttpResponse(f"Error updating visitor: {str(e)}", status=500)

        return redirect('visitors')

    return render(request, 'update_visitor.html', {'visitor': visitor})

@login_required
def delete_visitor(request, phone):
    try:
        print(f"Deleting visitor with phone: {phone}")
        visitor = table.get_item(Key={'phone': phone})['Item']
        name = visitor['name']

        table.delete_item(Key={'phone': phone})

        if visitor.get('photo_url'):
            s3_photo_key = visitor['photo_url'].replace(f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/photos/", "")
            s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_photo_key)

        exit_time = datetime.now(timezone.utc).isoformat()
        message = f"Visitor deleted: {name} (Phone: {phone}) at {exit_time}"
        sns.publish(TopicArn=settings.SNS_TOPIC_ARN, Message=message, Subject="Visitor Deleted")
    except Exception as e:
        print(f"Error deleting visitor: {str(e)}")
        return HttpResponse(f"Error deleting visitor: {str(e)}", status=500)

    return redirect('visitors')

@login_required
def manage_visitors(request):
    if request.method == 'POST':
        try:
            phone = request.POST['phone']
            exit_time = datetime.now(timezone.utc).isoformat()
            table.update_item(
                Key={'phone': phone},
                UpdateExpression="SET exit_time = :val",
                ExpressionAttributeValues={':val': exit_time}
            )

            response = table.get_item(Key={'phone': phone})
            name = response['Item']['name']
            message = f"Visitor exited: {name} (Phone: {phone}) at {exit_time}"
            sns.publish(TopicArn=settings.SNS_TOPIC_ARN, Message=message, Subject="Visitor Exit")
        except Exception as e:
            print(f"Error managing visitor: {str(e)}")
            return HttpResponse(f"Error managing visitor: {str(e)}", status=500)

        return redirect('manage_visitors')
    try:
        print("Attempting to scan DynamoDB table...")
        response = table.scan()
        visitors = response['Items']
        print(f"Successfully scanned {len(visitors)} visitors")
    except Exception as e:
        print(f"Error fetching visitors: {str(e)}")
        return HttpResponse(f"Error fetching visitors: {str(e)}", status=500)
    return render(request, 'manage_visitors.html', {'visitors': visitors})

@login_required
def reports(request):
    start_date = ''
    end_date = ''
    visitors = []
    if request.method == 'POST':
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        try:
            start_iso = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc).isoformat()
            end_iso = datetime.strptime(end_date, '%Y-%m-d').replace(tzinfo=timezone.utc).isoformat() + 'Z'
            response = table.scan(
                FilterExpression="entry_time BETWEEN :start AND :end",
                ExpressionAttributeValues={
                    ':start': start_iso,
                    ':end': end_iso
                }
            )
            visitors = response['Items']
        except ValueError as e:
            return render(request, 'reports.html', {'error': 'Invalid date format. Use YYYY-MM-DD.', 'start_date': start_date, 'end_date': end_date})
        except Exception as e:
            print(f"Error generating report: {str(e)}")
            return HttpResponse(f"Error generating report: {str(e)}", status=500)
    return render(request, 'reports.html', {'visitors': visitors, 'start_date': start_date, 'end_date': end_date})

@login_required
def search(request):
    try:
        query = request.GET.get('q', '')
        print(f"Searching for query: {query}")
        response = table.scan()
        visitors = [v for v in response['Items'] if query.lower() in v['name'].lower() or query in v['phone']]
        print(f"Found {len(visitors)} matching visitors")
    except Exception as e:
        print(f"Error searching visitors: {str(e)}")
        return HttpResponse(f"Error searching visitors: {str(e)}", status=500)
    return render(request, 'visitors.html', {'visitors': visitors})

def signup(request):
    if request.method == 'POST':
        try:
            form = UserCreationForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('login')
        except Exception as e:
            print(f"Error during signup: {str(e)}")
            return HttpResponse(f"Error during signup: {str(e)}", status=500)
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})