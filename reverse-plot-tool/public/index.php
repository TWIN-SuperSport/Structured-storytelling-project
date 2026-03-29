<?php

declare(strict_types=1);

use Psr\Http\Message\ResponseInterface as Response;
use Psr\Http\Message\ServerRequestInterface as Request;
use Slim\Factory\AppFactory;

require __DIR__ . '/../vendor/autoload.php';

$app = AppFactory::create();
$app->addRoutingMiddleware();
$app->addErrorMiddleware(true, true, true);

$app->get('/', function (Request $request, Response $response): Response {
    $html = file_get_contents(__DIR__ . '/../reverse-plot-tool.html');
    $response->getBody()->write($html);
    return $response->withHeader('Content-Type', 'text/html; charset=UTF-8');
});

$app->get('/healthz', function (Request $request, Response $response): Response {
    $response->getBody()->write(json_encode(['status' => 'ok'], JSON_UNESCAPED_UNICODE));
    return $response->withHeader('Content-Type', 'application/json; charset=UTF-8');
});

$app->run();
