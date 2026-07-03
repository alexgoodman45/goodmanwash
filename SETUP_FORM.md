# Quick form setup

The easiest path is to use Formspree or a similar static form service.

## 1. Create a free Formspree form
- Go to https://formspree.io/
- Create a new form
- Copy the form endpoint URL

## 2. Update the form in quote.html
Replace this line:

```html
<form class="quote-form" action="https://formspree.io/f/your-form-id" method="POST">
```

with your real endpoint:

```html
<form class="quote-form" action="https://formspree.io/f/your-real-form-id" method="POST">
```

## 3. Publish the site
Once the endpoint is added, the form will work on GitHub Pages without any local server.
