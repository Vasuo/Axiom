# -*- coding: utf-8 -*-
import pygame
import sys

#               PyGame
pygame.init()

#               
WIDTH = 800
HEIGHT = 600
FPS = 60

#      
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 120, 255)

#              
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("        ")
clock = pygame.time.Clock()