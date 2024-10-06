// static/chat.js

document.addEventListener("DOMContentLoaded", () => {
    const socket = io();

    const form = document.getElementById('chat-form');
    const input = document.getElementById('message-input');
    const messages = document.getElementById('messages');

    // Handle form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        if (input.value) {
            socket.emit('send_message', input.value);
            input.value = '';
        }
    });

    // Listen for incoming messages
    socket.on('receive_message', function(data) {
        const item = document.createElement('li');
        item.textContent = `${data.username}: ${data.message}`;
        messages.appendChild(item);
        window.scrollTo(0, document.body.scrollHeight);
    });

    // Only execute moderation functionalities if the user is a moderator
    {% if current_user.is_authenticated and current_user.is_mod %}
        // Fetch and display the list of users
        fetch('/api/users')
            .then(response => response.json())
            .then(data => {
                const userList = document.getElementById('user-list');
                data.users.forEach(user => {
                    const item = document.createElement('li');
                    item.textContent = user.username;
                    if (!user.is_mod && !user.is_banned) {  // Prevent mods from deleting other mods or already banned users
                        const banButton = document.createElement('button');
                        banButton.textContent = 'Ban';
                        banButton.onclick = () => banUser(user.id);
                        item.appendChild(banButton);
                    }
                    userList.appendChild(item);
                });
            });

        // Fetch and display the list of messages
        fetch('/api/messages')
            .then(response => response.json())
            .then(data => {
                const messageList = document.getElementById('message-list');
                data.messages.forEach(message => {
                    const item = document.createElement('li');
                    item.textContent = `${message.username}: ${message.content}`;
                    const deleteButton = document.createElement('button');
                    deleteButton.textContent = 'Delete';
                    deleteButton.onclick = () => deleteMessage(message.id);
                    item.appendChild(deleteButton);
                    messageList.appendChild(item);
                });
            });

        // Function to ban a user
        function banUser(userId) {
            fetch(`/api/ban_user/${userId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                location.reload();
            });
        }

        // Function to delete a message
        function deleteMessage(messageId) {
            fetch(`/api/delete_message/${messageId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                location.reload();
            });
        }
    {% endif %}
});
