from django import forms
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
import re

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'custom-input',
            'placeholder': 'Enter your email',
        })
    )

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'custom-input',
            'placeholder': 'Enter new password',
        })
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'custom-input',
            'placeholder': 'Confirm new password',
        })
    )

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1', '')
        if len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long.')
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('Password must include at least one uppercase letter.')
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError('Password must include at least one lowercase letter.')
        if not re.search(r'\d', password):
            raise forms.ValidationError('Password must include at least one number.')
        if not re.search(r'[^A-Za-z0-9]', password):
            raise forms.ValidationError('Password must include at least one special character.')
        return password
