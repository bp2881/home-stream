FROM node:alpine
RUN npm install -g http-server
WORKDIR /app
COPY . /app
EXPOSE 2005
CMD ["http-server", ".", "-p", "2005", "--cors"]
