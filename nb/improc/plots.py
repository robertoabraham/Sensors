import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np
import astropy.units as u


def alt_az_plot(current_position, target=None, figure_number=0):

    alt = current_position[0]
    az = current_position[1]
    
    fig = plt.figure(figure_number)
    fig.clf()
    ax = fig.add_subplot(projection = 'polar')
    
    plt.subplots_adjust(top=0.864, bottom = 0.076)

    # Setup labels
    ax.set_theta_zero_location('N')
    degree_sign = u'\N{DEGREE SIGN}'
    r_labels = [
        '90' + degree_sign,
        '',
        '60' + degree_sign,
        '',
        '30' + degree_sign,
        '',
        ''
    ]

    theta_labels = []
    az_label_offset=0.0*u.deg
    for chunk in range(0, 8):
        label_angle = (az_label_offset*(1/u.deg)) + (chunk*45.0)
        while label_angle >= 360.0:
            label_angle -= 360.0
        if chunk == 0:
            theta_labels.append('N ' + '\n' + str(label_angle) + degree_sign
                                + ' Az')
        elif chunk == 2:
            theta_labels.append('E' + '\n' + str(label_angle) + degree_sign)
        elif chunk == 4:
            theta_labels.append('S' + '\n' + str(label_angle) + degree_sign)
        elif chunk == 6:
            theta_labels.append('W' + '\n' + "  " + str(label_angle) + degree_sign)
        else:
            theta_labels.append(str(label_angle) + degree_sign)

    ax.set_rlim(1, 91)
    ax.grid(True, which='major')
    ax.set_thetagrids(range(0, 360, 45), theta_labels)
    ax.set_rgrids(range(1, 106, 15), r_labels, angle=-45)
    ax.set_title("Astro-Physics Equatorial Mount", va='bottom')

    # Go from alt-az to polar coordinates in radians.
    r = np.asarray([alt])
    r = 90.0 - r
    theta = np.asarray([az])
    theta = theta * (np.pi/180.0)
    ax.scatter(theta, r)
    
    if target:
        r = np.asarray([target[0]])
        r = 90.0 - r
        theta = np.asarray([target[1]])
        theta = theta * (np.pi/180.0)
        ax.scatter(theta, r, marker='x')

    plt.show(block=False)
    return fig