HTML page with rich code editor (see options below) and automatic preview. Horizontal or vertical split that can be dragged to resize. Save typed content in local storage as well.

Rich editor options:
- https://ace.c9.io/#nav=embedding (dead simple to setup)
- https://microsoft.github.io/monaco-editor/ (VSC actual editor, super powerful but overkill, and constant updates would be annoying)
- https://codemirror.net/

Hide behind basic Nginx auth. For Basic Auth can get the username from the Authorization header, it's base64 encoded in format username:password. Then can only allow access to that folder

Need server side element to take content on "Publish" button and save to a certain page name.

Read a list of folders, so we have ourplace.com/site/* with * being games/, space/, etc. that map to /var/www/site/*. So we read that site subdirectory. Then create radio buttons or dropdown on the HTML client side editor page to choose where to save, with an option to add a new page.

Need a way to upload images and other files too, but that can come later.
